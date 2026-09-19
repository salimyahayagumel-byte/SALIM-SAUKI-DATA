"""
SALIM SAUKI DATA
Persistent auto-signal history.

The in-memory cooldown cache is useful for speed, but it disappears when
Telegram restarts. This small SQLite layer makes sent-signal history survive
restarts without introducing a new external database dependency.
"""

import os
import sqlite3
import threading
import time
from typing import Dict, List, Optional, Tuple


class SignalHistory:
    def __init__(self, database_url: str = ""):
        self.path = self._resolve_path(database_url)
        self._lock = threading.Lock()
        self._initialize()

    @staticmethod
    def _resolve_path(database_url: str) -> str:
        value = str(database_url or os.getenv("DATABASE_URL", "") or "").strip()
        if value.startswith("sqlite:///./"):
            return value[len("sqlite:///./"):]
        if value.startswith("sqlite:///"):
            return value[len("sqlite:///"):]
        if not value or "://" in value:
            return "./salim_sauki_data.db"
        return value

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self):
        with self._lock:
            with self._connect() as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS signal_history (
                        signal_key TEXT PRIMARY KEY,
                        chain TEXT NOT NULL,
                        address TEXT NOT NULL,
                        symbol TEXT,
                        score REAL DEFAULT 0,
                        sent_at REAL NOT NULL
                    )
                    """
                )
                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_signal_history_sent_at "
                    "ON signal_history(sent_at)"
                )

    def load_recent(self, max_age_seconds: int) -> Dict[str, float]:
        cutoff = time.time() - max(0, int(max_age_seconds))
        with self._lock:
            with self._connect() as db:
                rows = db.execute(
                    "SELECT signal_key, sent_at FROM signal_history WHERE sent_at >= ?",
                    (cutoff,),
                ).fetchall()
        return {str(key): float(sent_at) for key, sent_at in rows}

    def record(
        self,
        signal_key: str,
        chain: str,
        address: str,
        symbol: str = "",
        score: float = 0,
        sent_at: Optional[float] = None,
    ) -> None:
        timestamp = float(sent_at or time.time())
        with self._lock:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO signal_history
                        (signal_key, chain, address, symbol, score, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(signal_key) DO UPDATE SET
                        chain=excluded.chain,
                        address=excluded.address,
                        symbol=excluded.symbol,
                        score=excluded.score,
                        sent_at=excluded.sent_at
                    """,
                    (
                        signal_key,
                        chain,
                        address,
                        symbol,
                        float(score or 0),
                        timestamp,
                    ),
                )

    def prune(self, max_rows: int = 5000) -> None:
        limit = max(100, int(max_rows))
        with self._lock:
            with self._connect() as db:
                db.execute(
                    """
                    DELETE FROM signal_history
                    WHERE signal_key IN (
                        SELECT signal_key
                        FROM signal_history
                        ORDER BY sent_at DESC
                        LIMIT -1 OFFSET ?
                    )
                    """,
                    (limit,),
                )

    def count(self) -> int:
        with self._lock:
            with self._connect() as db:
                row = db.execute(
                    "SELECT COUNT(*) FROM signal_history"
                ).fetchone()
        return int(row[0] if row else 0)
