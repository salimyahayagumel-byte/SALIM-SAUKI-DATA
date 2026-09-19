"""
SALIM SAUKI DATA
GROUP AUTO-CLEANUP BOT SERVICE

Deletes messages from one configured Telegram group after a delay.
The pending queue is stored in SQLite so scheduled deletions survive restarts.
"""

import asyncio
import logging
import os
import sqlite3
import time
from typing import List, Tuple

from telegram import Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)


class GroupCleanupService:
    def __init__(
        self,
        bot,
        chat_id: str,
        delete_after_seconds: int = 300,
        check_interval_seconds: int = 15,
        database_path: str = "./cleanup_messages.db",
    ):
        self.bot = bot
        self.chat_id = str(chat_id).strip()
        self.delete_after_seconds = max(60, int(delete_after_seconds))
        self.check_interval_seconds = max(5, int(check_interval_seconds))
        self.database_path = database_path
        self._task = None
        self._running = False

    def _db(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def init_db(self):
        with self._db() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_deletions (
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,
                    delete_at REAL NOT NULL,
                    PRIMARY KEY (chat_id, message_id)
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pending_delete_at
                ON pending_deletions(delete_at)
                """
            )

    def schedule(self, chat_id: int, message_id: int):
        delete_at = time.time() + self.delete_after_seconds

        with self._db() as db:
            db.execute(
                """
                INSERT INTO pending_deletions
                    (chat_id, message_id, delete_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, message_id)
                DO UPDATE SET delete_at=excluded.delete_at
                """,
                (str(chat_id), int(message_id), delete_at),
            )

    def _load_due(self, limit: int = 100) -> List[Tuple[str, int]]:
        now = time.time()

        with self._db() as db:
            rows = db.execute(
                """
                SELECT chat_id, message_id
                FROM pending_deletions
                WHERE delete_at <= ?
                ORDER BY delete_at ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()

        return [
            (str(chat_id), int(message_id))
            for chat_id, message_id in rows
        ]

    def _remove(self, chat_id: str, message_id: int):
        with self._db() as db:
            db.execute(
                """
                DELETE FROM pending_deletions
                WHERE chat_id=? AND message_id=?
                """,
                (str(chat_id), int(message_id)),
            )

    async def remember_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        message = update.effective_message
        chat = update.effective_chat

        if message is None or chat is None:
            return

        if chat.type not in {"group", "supergroup"}:
            return

        if self.chat_id and str(chat.id) != self.chat_id:
            return

        self.schedule(chat.id, message.message_id)

        logger.info(
            "Scheduled deletion | chat=%s message=%s after=%ss",
            chat.id,
            message.message_id,
            self.delete_after_seconds,
        )

    async def _loop(self):
        while self._running:
            try:
                due = self._load_due()

                for chat_id, message_id in due:
                    remove_after_attempt = False

                    try:
                        await self.bot.delete_message(
                            chat_id=chat_id,
                            message_id=message_id,
                        )

                        logger.info(
                            "Deleted | chat=%s message=%s",
                            chat_id,
                            message_id,
                        )
                        remove_after_attempt = True

                    except BadRequest as exc:
                        text = str(exc).lower()

                        # Telegram returns BadRequest for permanent cases
                        # such as an already deleted/non-existent message.
                        # Keep transient failures in the queue so they can
                        # be retried on the next cleanup cycle.
                        permanent = any(
                            marker in text
                            for marker in (
                                "message to delete not found",
                                "message can't be deleted",
                                "message can't be deleted for everyone",
                                "message is too old",
                            )
                        )

                        if permanent:
                            logger.warning(
                                "Permanent delete skip | chat=%s message=%s: %s",
                                chat_id,
                                message_id,
                                exc,
                            )
                            remove_after_attempt = True
                        else:
                            logger.warning(
                                "Temporary delete failure; will retry | "
                                "chat=%s message=%s: %s",
                                chat_id,
                                message_id,
                                exc,
                            )

                    except Forbidden as exc:
                        logger.error(
                            "Delete permission missing | chat=%s: %s",
                            chat_id,
                            exc,
                        )
                        # Permission may be restored later; keep queued.

                    except TelegramError as exc:
                        logger.error(
                            "Telegram delete error; will retry | "
                            "chat=%s message=%s: %s",
                            chat_id,
                            message_id,
                            exc,
                        )

                    if remove_after_attempt:
                        self._remove(chat_id, message_id)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("Cleanup loop error")

            await asyncio.sleep(self.check_interval_seconds)

    async def diagnose(self) -> bool:
        """Verify the cleanup bot can access the configured group."""
        try:
            me = await self.bot.get_me()
            member = await self.bot.get_chat_member(
                chat_id=self.chat_id,
                user_id=me.id,
            )

            status = str(member.status or "").lower()
            can_delete = bool(
                getattr(member, "can_delete_messages", False)
            )

            logger.info(
                "Cleanup diagnostic | bot=@%s id=%s | status=%s | can_delete_messages=%s",
                me.username or "unknown",
                me.id,
                status,
                can_delete,
            )

            if status != "administrator" or not can_delete:
                logger.error(
                    "Cleanup diagnostic FAILED: bot must be administrator "
                    "with Delete Messages permission."
                )
                return False

            return True

        except Exception as exc:
            logger.exception(
                "Cleanup diagnostic FAILED for chat=%s: %s",
                self.chat_id,
                exc,
            )
            return False

    async def start(self):
        if self._running:
            return

        self.init_db()
        self._running = True
        self._task = asyncio.create_task(self._loop())

        logger.info(
            "Group cleanup service started | chat=%s | delete_after=%ss",
            self.chat_id,
            self.delete_after_seconds,
        )

    async def stop(self):
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None

        logger.info("Group cleanup service stopped.")


def add_cleanup_handler(
    application: Application,
    service: GroupCleanupService,
):
    application.add_handler(
        MessageHandler(
            filters.ALL,
            service.remember_message,
        )
    )
