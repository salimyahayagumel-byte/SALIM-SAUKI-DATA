"""
SALIM SAUKI DATA
PNL TRACKER V8.1

Tracks the price performance of successfully sent GEM signals.
The tracker uses DexScreener prices, stores entries in SQLite, survives
restarts, sends milestone updates, and can warn about drawdown from the
best recorded PNL.

PNL here is price-based only. It does not include trading fees, slippage,
taxes, or the user's actual position size.
"""

import asyncio
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from services.dexscreener import DexScreener


class PNLTracker:

    DEFAULT_INTERVAL = 60
    DEFAULT_MILESTONES = (10, 25, 50, 100, 200, 500, 1000)
    DEFAULT_MAX_TRACKED = 500
    DEFAULT_DRAWDOWN_ALERT = 20.0

    def __init__(
        self,
        bot: Any,
        chat_id: str,
        database_url: str = "",
        interval: int = DEFAULT_INTERVAL,
        milestones: Optional[List[float]] = None,
        max_tracked: int = DEFAULT_MAX_TRACKED,
        enabled: bool = True,
        drawdown_alert: float = DEFAULT_DRAWDOWN_ALERT,
    ):
        self.bot = bot
        self.chat_id = str(chat_id or "").strip()
        self.path = self._resolve_path(database_url)
        self.interval = max(15, int(interval or self.DEFAULT_INTERVAL))
        self.milestones = sorted(
            set(
                float(value)
                for value in (milestones or self.DEFAULT_MILESTONES)
                if float(value) > 0
            )
        ) or list(self.DEFAULT_MILESTONES)
        self.max_tracked = max(50, int(max_tracked or self.DEFAULT_MAX_TRACKED))
        self.enabled = bool(enabled)
        self.drawdown_alert = max(
            1.0,
            float(drawdown_alert or self.DEFAULT_DRAWDOWN_ALERT),
        )
        self.dex = DexScreener()
        self.running = False
        self.task: Optional[asyncio.Task] = None
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
                    CREATE TABLE IF NOT EXISTS pnl_tracking (
                        signal_key TEXT PRIMARY KEY,
                        chain TEXT NOT NULL,
                        address TEXT NOT NULL,
                        symbol TEXT,
                        entry_price REAL NOT NULL,
                        current_price REAL NOT NULL,
                        highest_price REAL NOT NULL,
                        highest_pnl REAL DEFAULT 0,
                        last_milestone REAL DEFAULT 0,
                        drawdown_alerted_peak REAL DEFAULT 0,
                        started_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                columns = {
                    row[1]
                    for row in db.execute("PRAGMA table_info(pnl_tracking)").fetchall()
                }
                if "drawdown_alerted_peak" not in columns:
                    db.execute(
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN drawdown_alerted_peak REAL DEFAULT 0"
                    )
                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pnl_tracking_updated_at "
                    "ON pnl_tracking(updated_at)"
                )

    def add_signal(self, token: Dict[str, Any]) -> bool:
        signal_key = self._signal_key(token)
        if not signal_key:
            return False

        entry_price = self._number(token.get("price"))
        if entry_price <= 0:
            return False

        chain = str(token.get("chain", "") or "").lower().strip()
        address = str(token.get("address", "") or "").strip()
        symbol = str(token.get("symbol", "N/A") or "N/A").strip()
        now = time.time()

        with self._lock:
            with self._connect() as db:
                before = db.total_changes
                db.execute(
                    """
                    INSERT INTO pnl_tracking
                        (signal_key, chain, address, symbol, entry_price,
                         current_price, highest_price, highest_pnl,
                         last_milestone, drawdown_alerted_peak,
                         started_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
                    ON CONFLICT(signal_key) DO NOTHING
                    """,
                    (
                        signal_key,
                        chain,
                        address,
                        symbol,
                        entry_price,
                        entry_price,
                        entry_price,
                        now,
                        now,
                    ),
                )
                return db.total_changes > before

    async def start(self):
        if not self.enabled:
            print("⏸️ PNL Tracker disabled by configuration.")
            return

        if self.running:
            return

        if not self.chat_id:
            print("⚠️ PNL Tracker disabled: chat_id missing.")
            return

        self.running = True
        self.task = asyncio.create_task(self._run())
        print(
            "📈 PNL Tracker STARTED | "
            f"interval={self.interval}s | "
            f"milestones={self.milestones} | "
            f"drawdown=-{self.drawdown_alert:.0f}%"
        )

    def stop(self):
        self.running = False
        task = self.task
        self.task = None
        if task and not task.done():
            task.cancel()
        print("🛑 PNL Tracker STOPPED")

    async def _run(self):
        while self.running:
            started = time.time()
            try:
                await self.update_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"❌ PNL tracker error: {exc}")

            elapsed = time.time() - started
            await asyncio.sleep(max(1, self.interval - elapsed))

    async def update_once(self):
        rows = self._load_active()
        if not rows:
            return

        by_chain: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            by_chain.setdefault(row["chain"], []).append(row)

        for chain, chain_rows in by_chain.items():
            addresses = [row["address"] for row in chain_rows]
            prices = await self._fetch_prices(addresses, chain)
            for row in chain_rows:
                price = prices.get(row["address"])
                if price is None or price <= 0:
                    continue
                await self._process_price(row, price)

    async def _fetch_prices(
        self,
        addresses: List[str],
        chain: str,
    ) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        for start in range(0, len(addresses), 30):
            batch = addresses[start:start + 30]
            try:
                pairs = await self.dex.tokens(batch)
            except Exception as exc:
                print(
                    f"⚠️ PNL price lookup failed "
                    f"[{chain.upper()}]: {exc}"
                )
                continue

            if not isinstance(pairs, list):
                continue

            batch_set = set(batch)
            for pair in pairs:
                if not isinstance(pair, dict):
                    continue
                if str(pair.get("chainId", "") or "").lower() != chain:
                    continue

                base_token = pair.get("baseToken")
                address = (
                    str(base_token.get("address", "") or "").strip()
                    if isinstance(base_token, dict)
                    else ""
                )
                if address not in batch_set:
                    continue

                price = self._number(pair.get("priceUsd"))
                if price <= 0:
                    continue

                old = prices.get(address, 0.0)
                if price > old:
                    prices[address] = price

        return prices

    async def _process_price(self, row: Dict[str, Any], price: float):
        entry = self._number(row["entry_price"])
        if entry <= 0:
            return

        pnl = ((price - entry) / entry) * 100.0
        previous_highest_pnl = self._number(row["highest_pnl"])
        highest_price = max(self._number(row["highest_price"]), price)
        highest_pnl = max(previous_highest_pnl, pnl)
        old_milestone = self._number(row["last_milestone"])
        new_milestone = self._highest_reached(pnl)
        stored_milestone = max(old_milestone, new_milestone)

        self._update_row(
            signal_key=row["signal_key"],
            current_price=price,
            highest_price=highest_price,
            highest_pnl=highest_pnl,
            last_milestone=stored_milestone,
        )

        if new_milestone > old_milestone:
            await self._send_update(
                row=row,
                current_price=price,
                pnl=pnl,
                milestone=new_milestone,
                highest_pnl=highest_pnl,
                drawdown=0.0,
                alert_type="milestone",
            )

        # Alert once after a meaningful decline from a recorded high.
        drawdown = max(0.0, highest_pnl - pnl)
        alerted_peak = self._number(row.get("drawdown_alerted_peak"))
        new_peak_since_alert = highest_pnl > alerted_peak + 0.1
        should_alert_drawdown = (
            highest_pnl >= self.drawdown_alert
            and drawdown >= self.drawdown_alert
            and new_peak_since_alert
        )

        if should_alert_drawdown:
            self._mark_drawdown_alert(
                row["signal_key"],
                highest_pnl,
            )
            await self._send_update(
                row=row,
                current_price=price,
                pnl=pnl,
                milestone=stored_milestone,
                highest_pnl=highest_pnl,
                drawdown=drawdown,
                alert_type="drawdown",
            )

    def _highest_reached(self, pnl: float) -> float:
        reached = 0.0
        for milestone in self.milestones:
            if pnl >= milestone:
                reached = milestone
        return reached

    async def _send_update(
        self,
        row: Dict[str, Any],
        current_price: float,
        pnl: float,
        milestone: float,
        highest_pnl: float,
        drawdown: float = 0.0,
        alert_type: str = "milestone",
    ):
        symbol = row["symbol"]
        chain = str(row["chain"]).lower()
        chain_label = "🟣 Solana" if chain == "solana" else "🔵 Base"
        multiplier = 1 + (pnl / 100.0)

        title = (
            "📉 <b>SALIM SAUKI DATA — DRAWDOWN ALERT</b>"
            if alert_type == "drawdown"
            else "📈 <b>SALIM SAUKI DATA — PNL UPDATE</b>"
        )

        milestone_line = (
            f"┗ Milestone: <b>+{milestone:.0f}%</b>"
            if milestone > 0
            else "┗ Milestone: <b>None yet</b>"
        )

        message = "\n".join(
            [
                title,
                "━━━━━━━━━━━━━━━━━━━━",
                f"🟢 <b>${self._escape(symbol)}</b>",
                f"{chain_label}",
                "",
                "💰 <b>PRICE</b>",
                f"┗ Entry: <b>{self._format_price(row['entry_price'])}</b>",
                f"┗ Current: <b>{self._format_price(current_price)}</b>",
                "",
                "📊 <b>PNL</b>",
                f"┗ Current PNL: <b>{pnl:+.1f}%</b>",
                milestone_line,
                f"┗ Multiple: <b>{multiplier:.2f}X</b>",
                f"┗ Best PNL: <b>+{highest_pnl:.1f}%</b>",
                f"┗ Drawdown: <b>-{drawdown:.1f}%</b>" if drawdown > 0 else "",
                "",
                f"📄 <code>{self._escape(row['address'])}</code>",
                "",
                "⚠️ <i>PNL is price-based; fees/slippage are not included.</i>",
            ]
        )

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            if alert_type == "drawdown":
                print(
                    f"📉 PNL DRAWDOWN: ${symbol} "
                    f"PNL={pnl:+.1f}% / DD=-{drawdown:.1f}%"
                )
            else:
                print(
                    f"📈 PNL UPDATE: ${symbol} "
                    f"{pnl:+.1f}% / +{milestone:.0f}%"
                )
        except Exception as exc:
            print(f"❌ PNL Telegram error for ${symbol}: {exc}")

    def get_tracked(self, address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return tracked PNL rows, optionally filtered by token address."""
        normalized = str(address or "").strip()
        query = """
            SELECT signal_key, chain, address, symbol, entry_price,
                   current_price, highest_price, highest_pnl,
                   last_milestone, drawdown_alerted_peak,
                   started_at, updated_at
            FROM pnl_tracking
        """
        params: tuple = ()
        if normalized:
            # Accept either a plain contract address or chain:address.
            if ":" in normalized:
                chain, raw_address = normalized.split(":", 1)
                query += " WHERE lower(chain)=lower(?) AND lower(address)=lower(?)"
                params = (chain.strip(), raw_address.strip())
            else:
                query += " WHERE lower(address)=lower(?)"
                params = (normalized,)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params = (*params, self.max_tracked)

        with self._lock:
            with self._connect() as db:
                rows = db.execute(query, params).fetchall()

        columns = [
            "signal_key", "chain", "address", "symbol", "entry_price",
            "current_price", "highest_price", "highest_pnl",
            "last_milestone", "drawdown_alerted_peak", "started_at", "updated_at",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_pnl_rows(self, mode: str = "all") -> List[Dict[str, Any]]:
        """Return tracked rows using useful PNL filters for Telegram."""
        rows = self.get_tracked(None)
        mode = str(mode or "all").strip().lower()
        if mode in {"", "all", "summary"}:
            return rows

        if mode in {"winner", "winners", "profit", "profits", "green"}:
            return [row for row in rows if self._row_pnl(row) > 0]

        if mode in {"loser", "losers", "loss", "losses", "red"}:
            return [row for row in rows if self._row_pnl(row) < 0]

        if mode in {"breakeven", "flat", "zero"}:
            return [row for row in rows if abs(self._row_pnl(row)) < 0.01]

        multiplier_targets = {
            "2x": 100.0,
            "5x": 400.0,
            "10x": 900.0,
        }
        if mode in multiplier_targets:
            minimum = multiplier_targets[mode]
            return [row for row in rows if self._row_pnl(row) >= minimum]

        if mode in {"best", "top", "gainers"}:
            return sorted(rows, key=self._row_pnl, reverse=True)

        if mode in {"worst", "bottom", "losing"}:
            return sorted(rows, key=self._row_pnl)

        return []

    def get_pnl_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for all tracked positions."""
        rows = self.get_tracked(None)
        pnls = [self._row_pnl(row) for row in rows]
        winners = [value for value in pnls if value > 0]
        losers = [value for value in pnls if value < 0]
        return {
            "total": len(rows),
            "winners": len(winners),
            "losers": len(losers),
            "flat": len(pnls) - len(winners) - len(losers),
            "average_pnl": (sum(pnls) / len(pnls)) if pnls else 0.0,
            "best_pnl": max(pnls) if pnls else 0.0,
            "worst_pnl": min(pnls) if pnls else 0.0,
            "two_x": sum(1 for value in pnls if value >= 100),
            "five_x": sum(1 for value in pnls if value >= 400),
            "ten_x": sum(1 for value in pnls if value >= 900),
        }

    @staticmethod
    def _row_pnl(row: Dict[str, Any]) -> float:
        entry = PNLTracker._number(row.get("entry_price"))
        current = PNLTracker._number(row.get("current_price"))
        if entry <= 0:
            return 0.0
        return ((current - entry) / entry) * 100.0

    @staticmethod
    def format_pnl_summary(rows: List[Dict[str, Any]]) -> str:
        """Format a compact professional PNL summary."""
        if not rows:
            return "ℹ️ Babu token da ya dace da wannan PNL filter."

        stats = {
            "total": len(rows),
            "winners": sum(1 for row in rows if PNLTracker._row_pnl(row) > 0),
            "losers": sum(1 for row in rows if PNLTracker._row_pnl(row) < 0),
        }
        ordered = sorted(rows, key=PNLTracker._row_pnl, reverse=True)
        lines = [
            "📊 <b>SALIM SAUKI DATA — PNL SUMMARY</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📦 Tracked: <b>{stats['total']}</b>",
            f"🟢 Winners: <b>{stats['winners']}</b>",
            f"🔴 Losers: <b>{stats['losers']}</b>",
            "",
            "🏆 <b>TOP GAINERS</b>",
        ]
        for row in ordered[:5]:
            pnl = PNLTracker._row_pnl(row)
            multiple = 1.0 + pnl / 100.0
            symbol = PNLTracker._escape(row.get("symbol", "N/A"))
            lines.append(f"🟢 ${symbol}  <b>{pnl:+.1f}%</b>  ({multiple:.2f}X)")

        lines.extend(["", "📉 <b>BIGGEST LOSERS</b>"])
        for row in sorted(rows, key=PNLTracker._row_pnl)[:5]:
            pnl = PNLTracker._row_pnl(row)
            multiple = 1.0 + pnl / 100.0
            symbol = PNLTracker._escape(row.get("symbol", "N/A"))
            lines.append(f"🔴 ${symbol}  <b>{pnl:+.1f}%</b>  ({multiple:.2f}X)")

        lines.extend([
            "",
            "🎯 <b>MULTIPLES</b>",
            f"┗ 2X+: <b>{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 100)}</b>",
            f"┗ 5X+: <b>{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 400)}</b>",
            f"┗ 10X+: <b>{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 900)}</b>",
        ])
        return "\n".join(lines)

    @staticmethod
    def format_manual_pnl(row: Dict[str, Any]) -> str:
        """Format one tracked PNL row for the /pnl Telegram command."""
        entry = PNLTracker._number(row.get("entry_price"))
        current = PNLTracker._number(row.get("current_price"))
        highest = PNLTracker._number(row.get("highest_price"))
        highest_pnl = PNLTracker._number(row.get("highest_pnl"))
        pnl = ((current - entry) / entry * 100.0) if entry > 0 else 0.0
        multiple = 1.0 + (pnl / 100.0)
        change = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        chain = str(row.get("chain", "")).lower()
        chain_label = "🟣 Solana" if chain == "solana" else "🔵 Base" if chain == "base" else f"⚪ {chain.title()}"
        milestone = PNLTracker._number(row.get("last_milestone"))

        lines = [
            f"{change} <b>${PNLTracker._escape(row.get('symbol', 'N/A'))}</b>",
            chain_label,
            f"💰 Entry: <b>{PNLTracker._format_price(entry)}</b>",
            f"📍 Current: <b>{PNLTracker._format_price(current)}</b>",
            f"📊 PNL: <b>{pnl:+.1f}%</b>",
            f"🚀 Multiple: <b>{multiple:.2f}X</b>",
            f"🏆 Best PNL: <b>{highest_pnl:+.1f}%</b>",
            f"💵 Best Price: <b>{PNLTracker._format_price(highest)}</b>",
            f"🎯 Last Milestone: <b>{('+' + format(milestone, '.0f') + '%') if milestone > 0 else 'None'}</b>",
            f"📄 <code>{PNLTracker._escape(row.get('address', ''))}</code>",
        ]
        return "\n".join(lines)

    def _load_active(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._connect() as db:
                rows = db.execute(
                    """
                    SELECT signal_key, chain, address, symbol, entry_price,
                           current_price, highest_price, highest_pnl,
                           last_milestone, drawdown_alerted_peak,
                           started_at, updated_at
                    FROM pnl_tracking
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (self.max_tracked,),
                ).fetchall()

        columns = [
            "signal_key", "chain", "address", "symbol", "entry_price",
            "current_price", "highest_price", "highest_pnl",
            "last_milestone", "drawdown_alerted_peak", "started_at", "updated_at",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def _update_row(
        self,
        signal_key: str,
        current_price: float,
        highest_price: float,
        highest_pnl: float,
        last_milestone: float,
    ):
        with self._lock:
            with self._connect() as db:
                db.execute(
                    """
                    UPDATE pnl_tracking
                    SET current_price=?, highest_price=?, highest_pnl=?,
                        last_milestone=?, updated_at=?
                    WHERE signal_key=?
                    """,
                    (
                        current_price,
                        highest_price,
                        highest_pnl,
                        last_milestone,
                        time.time(),
                        signal_key,
                    ),
                )

    def _mark_drawdown_alert(self, signal_key: str, peak_pnl: float):
        with self._lock:
            with self._connect() as db:
                db.execute(
                    """
                    UPDATE pnl_tracking
                    SET drawdown_alerted_peak=?
                    WHERE signal_key=?
                    """,
                    (peak_pnl, signal_key),
                )

    @staticmethod
    def _signal_key(token: Dict[str, Any]) -> str:
        chain = str(token.get("chain", "") or "").lower().strip()
        address = str(token.get("address", "") or "").strip()
        if not chain or not address:
            return ""
        return f"{chain}:{address}"

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _escape(value: Any) -> str:
        text = str(value or "")
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def _format_price(value: float) -> str:
        value = float(value or 0)
        if value >= 1:
            return f"${value:,.6f}".rstrip("0").rstrip(".")
        if value >= 0.01:
            return f"${value:.8f}".rstrip("0").rstrip(".")
        return f"${value:.12f}".rstrip("0").rstrip(".")
