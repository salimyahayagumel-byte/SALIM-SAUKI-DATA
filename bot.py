import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from telegram.request import HTTPXRequest

from config import (
    BOT_TOKEN,
    CLEANUP_BOT_TOKEN,
    CLEANUP_CHAT_ID,
    CLEANUP_DELETE_AFTER_SECONDS,
    CLEANUP_CHECK_INTERVAL,
    CLEANUP_DATABASE_PATH,
    AUTO_SIGNAL_CHAT_ID,
    AUTO_SIGNAL_ENABLED,
    AUTO_SIGNAL_INTERVAL,
    AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN,
    AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN,
    PNL_TRACKER_ENABLED,
    PNL_TRACKER_INTERVAL,
    PNL_TRACKER_MAX_TRACKED,
)

from handlers.start import start
from handlers.scan import scan
from handlers.analyze import analyze
from handlers.help import help_command
from handlers.status import status
from handlers.health import health
from handlers.pnl import pnl
from handlers.autostatus import autostatus

from services.auto_signal import AutoSignalEngine
from services.group_cleanup import (
    GroupCleanupService,
    add_cleanup_handler,
)


# =========================================
# LOGGING
# =========================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================
# AUTO SIGNAL SETTINGS
# =========================================



# =========================================
# GLOBAL AUTO SIGNAL ENGINE
# =========================================

auto_signal_engine = None
auto_signal_task = None

cleanup_app = None
cleanup_service = None
cleanup_uses_main_app = False


# =========================================
# ERROR HANDLER
# =========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram update error:",
        exc_info=context.error,
    )


# =========================================
# AUTO SIGNAL STARTER
# =========================================

async def start_auto_signals(
    application: Application,
):

    global auto_signal_engine

    if not AUTO_SIGNAL_CHAT_ID:

        print(
            "⚠️ AUTO_SIGNAL_CHAT_ID ba a saita ba."
        )

        print(
            "⏭️ Auto signals ba za su aika Telegram ba."
        )

        return

    print(
        "========================================"
    )

    print(
        "💎 DEX ANALYSIS BOT — AUTO SIGNAL"
    )

    print(
        "========================================"
    )

    print(
        f"📡 Chat ID: {AUTO_SIGNAL_CHAT_ID}"
    )

    print(
        f"⏱️ Interval: {AUTO_SIGNAL_INTERVAL}s"
    )

    auto_signal_engine = AutoSignalEngine(
        bot=application.bot,
        chat_id=AUTO_SIGNAL_CHAT_ID,
        interval=AUTO_SIGNAL_INTERVAL,
        max_signals_per_scan=AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN,
        max_signals_per_chain=AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN,
    )

    if PNL_TRACKER_ENABLED:
        auto_signal_engine.pnl_tracker.interval = max(15, PNL_TRACKER_INTERVAL)
        auto_signal_engine.pnl_tracker.max_tracked = max(50, PNL_TRACKER_MAX_TRACKED)

    application.bot_data["auto_signal_engine"] = auto_signal_engine

    await auto_signal_engine.start()


# =========================================
# MAIN BOT
# =========================================

async def run_bot():

    global auto_signal_task
    global auto_signal_engine
    global cleanup_app
    global cleanup_service
    global cleanup_uses_main_app

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN baya cikin .env"
        )

    # =====================================
    # TELEGRAM NETWORK SETTINGS
    # =====================================

    # Telegram connectivity fix:
    # curl/httpx direct requests work from Termux, but Telegram polling
    # can inherit proxy/environment settings through httpx. Disable those
    # environment settings and force HTTP/1.1 for a more reliable mobile
    # connection.
    telegram_httpx_kwargs = {
        "trust_env": False,
        "http2": False,
    }

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
        http_version="1.1",
        httpx_kwargs=telegram_httpx_kwargs,
    )

    get_updates_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
        http_version="1.1",
        httpx_kwargs=telegram_httpx_kwargs,
    )

    # =====================================
    # APPLICATION
    # =====================================

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(
            get_updates_request
        )
        .build()
    )

    # =====================================
    # COMMANDS
    # =====================================

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "scan",
            scan,
        )
    )

    app.add_handler(
        CommandHandler(
            "analyze",
            analyze,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status,
        )
    )

    app.add_handler(
        CommandHandler(
            "health",
            health,
        )
    )

    app.add_handler(
        CommandHandler(
            "pnl",
            pnl,
        )
    )

    app.add_handler(
        CommandHandler(
            "autostatus",
            autostatus,
        )
    )

    # =====================================
    # ERROR HANDLER
    # =====================================

    app.add_error_handler(
        error_handler
    )

    # =====================================
    # STARTUP
    # =====================================

    print(
        "========================================"
    )

    print(
        "🧠 DEX ANALYSIS BOT"
    )

    print(
        "💎 DEX ANALYSIS BOT"
    )

    print(
        "========================================"
    )

    print(
        "🤖 Bot yana farawa..."
    )

    # =====================================
    # INITIALIZE
    # =====================================

    await app.initialize()

    print(
        "✅ Telegram API connected"
    )

    # =====================================
    # START APPLICATION
    # =====================================

    await app.start()

    print(
        "✅ Application started"
    )

    # =====================================
    # START POLLING
    # =====================================

    await app.updater.start_polling(
        drop_pending_updates=True
    )

    print(
        "🚀 BOT YANA AIKI!"
    )

    print(
        "📡 Waiting for Telegram messages..."
    )

    # =====================================
    # START GROUP AUTO-CLEANUP
    # =====================================
    #
    # IMPORTANT:
    # Telegram allows only one active getUpdates
    # consumer per bot token. If the cleanup token
    # is accidentally the same as BOT_TOKEN, do NOT
    # start a second polling Application. Instead,
    # attach cleanup to the already-running main bot.
    # This prevents the classic Telegram 409 conflict.
    # =====================================

    if CLEANUP_BOT_TOKEN and CLEANUP_CHAT_ID:

        print(
            "🧹 Starting Group Cleanup..."
        )

        if CLEANUP_BOT_TOKEN == BOT_TOKEN:

            cleanup_uses_main_app = True

            print(
                "ℹ️ Cleanup token matches BOT_TOKEN."
            )

            print(
                "ℹ️ Using the main Telegram bot for cleanup "
                "to avoid getUpdates conflict."
            )

            cleanup_service = GroupCleanupService(
                bot=app.bot,
                chat_id=CLEANUP_CHAT_ID,
                delete_after_seconds=CLEANUP_DELETE_AFTER_SECONDS,
                check_interval_seconds=CLEANUP_CHECK_INTERVAL,
                database_path=CLEANUP_DATABASE_PATH,
            )

            add_cleanup_handler(
                app,
                cleanup_service,
            )

            await cleanup_service.diagnose()
            await cleanup_service.start()

        else:

            # Separate HTTP clients avoid sharing the same
            # Telegram transport between two Applications.
            cleanup_request = HTTPXRequest(
                connect_timeout=30.0,
                read_timeout=60.0,
                write_timeout=60.0,
                pool_timeout=30.0,
                http_version="1.1",
                httpx_kwargs=telegram_httpx_kwargs,
            )

            cleanup_get_updates_request = HTTPXRequest(
                connect_timeout=30.0,
                read_timeout=60.0,
                write_timeout=60.0,
                pool_timeout=30.0,
                http_version="1.1",
                httpx_kwargs=telegram_httpx_kwargs,
            )

            cleanup_app = (
                Application.builder()
                .token(CLEANUP_BOT_TOKEN)
                .request(cleanup_request)
                .get_updates_request(
                    cleanup_get_updates_request
                )
                .build()
            )

            cleanup_service = GroupCleanupService(
                bot=cleanup_app.bot,
                chat_id=CLEANUP_CHAT_ID,
                delete_after_seconds=CLEANUP_DELETE_AFTER_SECONDS,
                check_interval_seconds=CLEANUP_CHECK_INTERVAL,
                database_path=CLEANUP_DATABASE_PATH,
            )

            add_cleanup_handler(
                cleanup_app,
                cleanup_service,
            )

            cleanup_app.add_error_handler(
                error_handler
            )

            await cleanup_app.initialize()

            print(
                "✅ Cleanup Telegram API connected"
            )

            if not await cleanup_service.diagnose():

                print(
                    "⚠️ Cleanup diagnostic failed. "
                    "The cleanup service will still start, "
                    "but Telegram permissions/chat ID must be fixed."
                )

            await cleanup_app.start()

            if cleanup_app.updater:

                await cleanup_app.updater.start_polling(
                    drop_pending_updates=True
                )

            await cleanup_service.start()

        print(
            "🧹 Cleanup Bot is ACTIVE"
        )

        print(
            f"⏱️ Messages will be deleted after "
            f"{CLEANUP_DELETE_AFTER_SECONDS}s"
        )

        print(
            f"📡 Cleanup Chat ID: {CLEANUP_CHAT_ID}"
        )

    else:

        print(
            "⚠️ Group Cleanup Bot disabled."
        )

        print(
            "⚠️ Set CLEANUP_BOT_TOKEN and "
            "CLEANUP_CHAT_ID inside .env"
        )

    # =====================================
    # START AUTO SIGNAL ENGINE
    # =====================================

    if AUTO_SIGNAL_ENABLED and AUTO_SIGNAL_CHAT_ID:

        print(
            "🚀 Starting Auto Signal Engine..."
        )

        auto_signal_task = asyncio.create_task(
            start_auto_signals(
                app
            )
        )

    else:

        print(
            "⚠️ Auto Signal Engine disabled."
        )

        print(
            "⚠️ Set AUTO_SIGNAL_CHAT_ID "
            "inside .env"
        )

    # =====================================
    # KEEP BOT ALIVE
    # =====================================

    try:

        while True:

            await asyncio.sleep(
                3600
            )

    except asyncio.CancelledError:

        print(
            "🛑 Bot task cancelled."
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot stopped by user."
        )

    finally:

        print(
            "⏳ Shutting down..."
        )

        # =================================
        # STOP AUTO SIGNAL ENGINE
        # =================================

        if auto_signal_engine:

            auto_signal_engine.stop()

        if auto_signal_task:

            if not auto_signal_task.done():

                auto_signal_task.cancel()

                try:

                    await auto_signal_task

                except asyncio.CancelledError:

                    pass

                except Exception as exc:

                    logger.error(
                        "Auto signal shutdown error: %s",
                        exc,
                    )

        # =================================
        # STOP GROUP CLEANUP BOT
        # =================================

        if cleanup_service:

            await cleanup_service.stop()

        if cleanup_app and not cleanup_uses_main_app:

            if cleanup_app.updater:

                if cleanup_app.updater.running:

                    await cleanup_app.updater.stop()

            if cleanup_app.running:

                await cleanup_app.stop()

            await cleanup_app.shutdown()

        # =================================
        # STOP TELEGRAM
        # =================================

        if app.updater:

            if app.updater.running:

                await app.updater.stop()

        if app.running:

            await app.stop()

        await app.shutdown()

        print(
            "✅ Bot shutdown complete."
        )


# =========================================
# ENTRY POINT
# =========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run_bot()
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot stopped."
        )
