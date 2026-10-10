"""Persistent 24-hour Telegram summary counters for MASFOX.

This database is deliberately separate from signal history and PNL databases.
It records only aggregate reporting counters and never deletes bot history.
"""
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DASHBOARD_REPORT_DB", str(ROOT / "dashboard_report.db")))
PERIOD_SECONDS = 24 * 60 * 60


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS report_cycle (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        started_at REAL NOT NULL,
        scans INTEGER NOT NULL DEFAULT 0,
        candidates_found INTEGER NOT NULL DEFAULT 0,
        signals_sent INTEGER NOT NULL DEFAULT 0,
        strong_gem INTEGER NOT NULL DEFAULT 0,
        gem_signal INTEGER NOT NULL DEFAULT 0,
        early_gem INTEGER NOT NULL DEFAULT 0
    )""")
    conn.execute("INSERT OR IGNORE INTO report_cycle (id, started_at) VALUES (1, ?)", (time.time(),))
    conn.commit()


def record_scan(candidates_found: int) -> None:
    """Count one completed auto-scan and the candidates it returned."""
    with _connect() as conn:
        _ensure(conn)
        conn.execute("UPDATE report_cycle SET scans=scans+1, candidates_found=candidates_found+? WHERE id=1", (max(0, int(candidates_found)),))
        conn.commit()


def record_signal(status: str) -> None:
    """Count a signal only after Telegram delivery succeeds."""
    value = str(status or "").upper()
    column = "early_gem"
    if "STRONG" in value:
        column = "strong_gem"
    elif "GEM SIGNAL" in value or value == "GEM":
        column = "gem_signal"
    with _connect() as conn:
        _ensure(conn)
        conn.execute(f"UPDATE report_cycle SET signals_sent=signals_sent+1, {column}={column}+1 WHERE id=1")
        conn.commit()


def report_if_due(force: bool = False) -> Dict[str, Any] | None:
    """Return and reset a report only when the persisted 24h period is due."""
    now = time.time()
    with _connect() as conn:
        _ensure(conn)
        row = conn.execute("SELECT * FROM report_cycle WHERE id=1").fetchone()
        if not row or (not force and now - float(row["started_at"]) < PERIOD_SECONDS):
            return None
        report = dict(row)
        # Start the next cycle only when the caller has obtained the report.
        conn.execute("UPDATE report_cycle SET started_at=?, scans=0, candidates_found=0, signals_sent=0, strong_gem=0, gem_signal=0, early_gem=0 WHERE id=1", (now,))
        conn.commit()
        return report


def restore_report(report: Dict[str, Any]) -> None:
    """Restore counters if Telegram sending failed, so the report isn't lost."""
    with _connect() as conn:
        _ensure(conn)
        conn.execute("""UPDATE report_cycle SET started_at=?, scans=scans+?, candidates_found=candidates_found+?,
            signals_sent=signals_sent+?, strong_gem=strong_gem+?, gem_signal=gem_signal+?, early_gem=early_gem+? WHERE id=1""",
            (float(report.get("started_at", time.time())), int(report.get("scans", 0)), int(report.get("candidates_found", 0)),
             int(report.get("signals_sent", 0)), int(report.get("strong_gem", 0)), int(report.get("gem_signal", 0)), int(report.get("early_gem", 0))))
        conn.commit()
