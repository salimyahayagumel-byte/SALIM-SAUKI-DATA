"""
Persistent signal history backed by Render PostgreSQL when DATABASE_URL is a
PostgreSQL URL; SQLite remains supported for local development.
"""
import os
import json
import sqlite3
import threading
import time
from typing import Dict, List, Optional

class SignalHistory:
    def __init__(self, database_url: str = ""):
        self.database_url = str(database_url or os.getenv("DATABASE_URL", "") or "").strip()
        self.is_postgres = self.database_url.startswith(("postgres://", "postgresql://"))
        self.path = self._resolve_path(self.database_url)
        self._lock = threading.Lock()
        if self.is_postgres:
            try:
                import psycopg
            except ImportError as exc:
                raise RuntimeError("PostgreSQL DATABASE_URL is set but psycopg is not installed") from exc
            self._pg = psycopg
        self._initialize()

    @staticmethod
    def _resolve_path(value: str) -> str:
        if value.startswith("sqlite:///./"):
            return value[len("sqlite:///./"):]
        if value.startswith("sqlite:///"):
            return value[len("sqlite:///"):]
        if not value or "://" in value:
            return "./salim_sauki_data.db"
        return value

    def _connect(self):
        if self.is_postgres:
            return self._pg.connect(self.database_url, connect_timeout=10)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self):
        with self._lock, self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    signal_key TEXT PRIMARY KEY,
                    chain TEXT NOT NULL,
                    address TEXT NOT NULL,
                    symbol TEXT,
                    score DOUBLE PRECISION DEFAULT 0,
                    sent_at DOUBLE PRECISION NOT NULL,
                    token_json TEXT
                )
            """)
            if not self.is_postgres:
                columns = {row[1] for row in db.execute("PRAGMA table_info(signal_history)").fetchall()}
                if "token_json" not in columns:
                    db.execute("ALTER TABLE signal_history ADD COLUMN token_json TEXT")
            else:
                db.execute("ALTER TABLE signal_history ADD COLUMN IF NOT EXISTS token_json TEXT")
            db.execute("CREATE INDEX IF NOT EXISTS idx_signal_history_sent_at ON signal_history(sent_at)")

    def load_recent(self, max_age_seconds: int = 0) -> Dict[str, float]:
        """Load every previously delivered token key for permanent deduplication.

        max_age_seconds remains accepted for backwards compatibility, but sent
        token identities must not expire merely because a cooldown elapsed.
        """
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT signal_key, sent_at FROM signal_history").fetchall()
        return {str(key).lower(): float(sent_at) for key, sent_at in rows}

    def record(self, signal_key: str, chain: str, address: str, symbol: str = "", score: float = 0, sent_at: Optional[float] = None, token: Optional[Dict] = None) -> None:
        timestamp = float(sent_at or time.time())
        sql = """
            INSERT INTO signal_history
                (signal_key, chain, address, symbol, score, sent_at, token_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(signal_key) DO UPDATE SET
                chain=excluded.chain, address=excluded.address, symbol=excluded.symbol,
                score=excluded.score, sent_at=excluded.sent_at, token_json=excluded.token_json
        """
        if not self.is_postgres:
            sql = sql.replace("%s", "?")
        with self._lock, self._connect() as db:
            db.execute(sql, (signal_key, chain, address, symbol, float(score or 0), timestamp, json.dumps(token or {}, ensure_ascii=False, default=str)))

    def recent_signals(self, limit: int = 100) -> List[Dict]:
        limit = max(1, min(int(limit or 100), 500))
        sql = "SELECT signal_key, chain, address, symbol, score, sent_at, token_json FROM signal_history ORDER BY sent_at DESC LIMIT %s"
        if not self.is_postgres:
            sql = sql.replace("%s", "?")
        with self._lock, self._connect() as db:
            rows = db.execute(sql, (limit,)).fetchall()
        result = []
        for key, chain, address, symbol, score, sent_at, token_json in rows:
            try: token = json.loads(token_json) if token_json else {}
            except Exception: token = {}
            if not isinstance(token, dict): token = {}
            token.setdefault("signal_key", key); token.setdefault("chain", chain)
            token.setdefault("address", address); token.setdefault("symbol", symbol or "")
            token.setdefault("recommendation_score", score or 0); token.setdefault("sent_at", sent_at)
            result.append(token)
        return result

    def prune(self, max_rows: int = 5000) -> None:
        limit = max(100, int(max_rows))
        with self._lock, self._connect() as db:
            if self.is_postgres:
                db.execute("""
                    DELETE FROM signal_history
                    WHERE signal_key IN (
                        SELECT signal_key FROM signal_history
                        ORDER BY sent_at DESC OFFSET %s
                    )
                """, (limit,))
            else:
                db.execute("""
                    DELETE FROM signal_history WHERE signal_key IN (
                        SELECT signal_key FROM signal_history ORDER BY sent_at DESC LIMIT -1 OFFSET ?
                    )
                """, (limit,))

    def count(self) -> int:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT COUNT(*) FROM signal_history").fetchone()
        return int(row[0] if row else 0)
