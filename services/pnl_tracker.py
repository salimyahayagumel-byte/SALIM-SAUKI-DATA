"""
SALIM SAUKI DATA
PNL TRACKER V9.2

Market-cap-based PNL tracking for successfully delivered GEM signals. Price is retained as supporting market data.

Key fixes in V9.1:
    - Tracks chain + token contract + entry pair address.
    - Uses the same DexScreener pair used for the signal whenever possible.
    - Never selects the highest-priced pool just because its price is higher.
    - If the original pair disappears, falls back to the most-liquid pool for
      that token on the same chain.
    - Explicitly closes SQLite connections to prevent ResourceWarning leaks.
    - Preserves milestone, drawdown, Telegram /pnl filters and restart safety.
    - Uses entry/current market cap as the primary PNL metric.
    - Keeps price data for reference and pair-aware market selection.
    - It is not a user's actual wallet PNL.

PNL does not include trading fees, slippage, taxes, position size, or execution
price differences.
"""

import asyncio
import os
import sqlite3
from datetime import datetime
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

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
        self.max_tracked = max(
            50,
            int(max_tracked or self.DEFAULT_MAX_TRACKED),
        )
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
        value = str(
            database_url
            or os.getenv("DATABASE_URL", "")
            or ""
        ).strip()

        if value.startswith("sqlite:///./"):
            return value[len("sqlite:///./"):]

        if value.startswith("sqlite:///"):
            return value[len("sqlite:///"):]

        if not value or "://" in value:
            return "./salim_sauki_data.db"

        return value

    def _connect(self) -> sqlite3.Connection:
        """Open one SQLite connection.

        Callers should use _db() so the connection is always closed.
        """
        connection = sqlite3.connect(
            self.path,
            timeout=10,
        )
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        """Context manager that commits/rolls back and ALWAYS closes."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._lock:
            with self._db() as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pnl_tracking (
                        signal_key TEXT PRIMARY KEY,
                        chain TEXT NOT NULL,
                        address TEXT NOT NULL,
                        symbol TEXT,
                        pair_address TEXT,
                        pair_created REAL DEFAULT 0,
                        twitter_url TEXT DEFAULT '',
                        telegram_url TEXT DEFAULT '',
                        website_url TEXT DEFAULT '',
                        entry_market_cap REAL DEFAULT 0,
                        current_market_cap REAL DEFAULT 0,
                        highest_market_cap REAL DEFAULT 0,
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
                    for row in db.execute(
                        "PRAGMA table_info(pnl_tracking)"
                    ).fetchall()
                }

                migrations = {
                    "pair_address": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN pair_address TEXT"
                    ),
                    "drawdown_alerted_peak": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN drawdown_alerted_peak REAL DEFAULT 0"
                    ),
                    "entry_market_cap": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN entry_market_cap REAL DEFAULT 0"
                    ),
                    "current_market_cap": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN current_market_cap REAL DEFAULT 0"
                    ),
                    "highest_market_cap": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN highest_market_cap REAL DEFAULT 0"
                    ),
                    "pair_created": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN pair_created REAL DEFAULT 0"
                    ),
                    "twitter_url": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN twitter_url TEXT DEFAULT ''"
                    ),
                    "telegram_url": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN telegram_url TEXT DEFAULT ''"
                    ),
                    "website_url": (
                        "ALTER TABLE pnl_tracking "
                        "ADD COLUMN website_url TEXT DEFAULT ''"
                    ),
                }

                for column, statement in migrations.items():
                    if column not in columns:
                        db.execute(statement)

                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pnl_tracking_updated_at "
                    "ON pnl_tracking(updated_at)"
                )

                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pnl_tracking_address "
                    "ON pnl_tracking(chain, address)"
                )

                db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pnl_tracking_pair "
                    "ON pnl_tracking(pair_address)"
                )

    def add_signal(self, token: Dict[str, Any]) -> bool:
        """Start tracking a successfully delivered signal.

        The scanner already supplies the DexScreener pair address in
        token['pair']. Storing it makes future PNL updates price the same
        market instead of accidentally choosing a different pool.
        """
        signal_key = self._signal_key(token)
        if not signal_key:
            return False

        entry_price = self._number(token.get("price"))
        entry_market_cap = self._number(
            token.get("marketcap", token.get("market_cap"))
        )
        if entry_price <= 0 or entry_market_cap <= 0:
            return False

        chain = str(
            token.get("chain", "")
            or ""
        ).lower().strip()

        address = str(
            token.get("address", "")
            or ""
        ).strip()

        symbol = str(
            token.get("symbol", "N/A")
            or "N/A"
        ).strip()

        pair_address = str(
            token.get("pair")
            or token.get("pairAddress")
            or ""
        ).strip()

        pair_created = self._number(
            token.get("pair_created", token.get("pairCreatedAt"))
        )
        twitter_url = str(token.get("twitter_url", "") or "").strip()
        telegram_url = str(token.get("telegram_url", "") or "").strip()
        website_url = str(token.get("website_url", "") or "").strip()

        now = time.time()

        with self._lock:
            with self._db() as db:
                before = db.total_changes

                db.execute(
                    """
                    INSERT INTO pnl_tracking
                        (
                            signal_key,
                            chain,
                            address,
                            symbol,
                            pair_address,
                            pair_created,
                            twitter_url,
                            telegram_url,
                            website_url,
                            entry_market_cap,
                            current_market_cap,
                            highest_market_cap,
                            entry_price,
                            current_price,
                            highest_price,
                            highest_pnl,
                            last_milestone,
                            drawdown_alerted_peak,
                            started_at,
                            updated_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
                    ON CONFLICT(signal_key) DO NOTHING
                    """,
                    (
                        signal_key,
                        chain,
                        address,
                        symbol,
                        pair_address,
                        pair_created,
                        twitter_url,
                        telegram_url,
                        website_url,
                        entry_market_cap,
                        entry_market_cap,
                        entry_market_cap,
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
            await asyncio.sleep(
                max(1, self.interval - elapsed)
            )

    async def update_once(self):
        rows = self._load_active()

        if not rows:
            return

        by_chain: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            chain = str(row.get("chain", "") or "").lower().strip()
            if chain:
                by_chain.setdefault(chain, []).append(row)

        for chain, chain_rows in by_chain.items():
            metrics = await self._fetch_pair_metrics(chain_rows, chain)

            for row in chain_rows:
                metric = metrics.get(row["signal_key"])
                if not metric:
                    continue

                price = self._number(metric.get("price"))
                market_cap = self._number(metric.get("market_cap"))

                if market_cap <= 0:
                    continue

                await self._process_market_cap(
                    row,
                    market_cap,
                    price,
                )

    async def _fetch_pair_metrics(
        self,
        rows: List[Dict[str, Any]],
        chain: str,
    ) -> Dict[str, Dict[str, float]]:
        """Return price + market cap from the correct DexScreener pool.

        Selection priority:
            1. Exact pair used at signal entry.
            2. If that pair is gone, the most-liquid valid pool for the
               same token on the same chain.

        The selected pool supplies both price and market cap so the two
        metrics never come from different pools.
        """
        metrics: Dict[str, Dict[str, float]] = {}

        for start in range(0, len(rows), 30):
            batch_rows = rows[start:start + 30]
            addresses = [
                str(row.get("address", "") or "").strip()
                for row in batch_rows
                if str(row.get("address", "") or "").strip()
            ]
            if not addresses:
                continue

            try:
                pairs = await self.dex.tokens(addresses)
            except Exception as exc:
                print(f"⚠️ PNL market lookup failed [{chain.upper()}]: {exc}")
                continue

            if not isinstance(pairs, list):
                continue

            wanted = set(addresses)
            row_by_key = {row["signal_key"]: row for row in batch_rows}
            signal_keys_by_address: Dict[str, List[str]] = {}
            for row in batch_rows:
                address = str(row.get("address", "") or "").strip()
                if address:
                    signal_keys_by_address.setdefault(address, []).append(row["signal_key"])

            exact: Dict[str, Tuple[float, float, float]] = {}
            fallback: Dict[str, Tuple[float, float, float]] = {}

            for pair in pairs:
                if not isinstance(pair, dict):
                    continue
                if str(pair.get("chainId", "") or "").lower().strip() != chain:
                    continue

                base_token = pair.get("baseToken")
                if not isinstance(base_token, dict):
                    continue
                address = str(base_token.get("address", "") or "").strip()
                if address not in wanted:
                    continue

                price = self._number(pair.get("priceUsd"))
                market_cap = self._number(pair.get("marketCap"))
                if market_cap <= 0:
                    market_cap = self._number(pair.get("fdv"))
                if price <= 0 and market_cap <= 0:
                    continue

                liquidity_data = pair.get("liquidity")
                liquidity = (
                    self._number(liquidity_data.get("usd"))
                    if isinstance(liquidity_data, dict) else 0.0
                )
                pair_address = str(pair.get("pairAddress", "") or "").strip()
                metric = (liquidity, price, market_cap)

                for signal_key in signal_keys_by_address.get(address, []):
                    row = row_by_key.get(signal_key)
                    if not row:
                        continue
                    stored_pair = str(row.get("pair_address", "") or "").strip()
                    if stored_pair and pair_address.lower() == stored_pair.lower():
                        if signal_key not in exact or liquidity > exact[signal_key][0]:
                            exact[signal_key] = metric
                    if signal_key not in fallback or liquidity > fallback[signal_key][0]:
                        fallback[signal_key] = metric

            for row in batch_rows:
                signal_key = row["signal_key"]
                selected = exact.get(signal_key) or fallback.get(signal_key)
                if selected:
                    metrics[signal_key] = {
                        "price": selected[1],
                        "market_cap": selected[2],
                    }

        return metrics

    async def _fetch_prices(
        self,
        rows: List[Dict[str, Any]],
        chain: str,
    ) -> Dict[str, float]:
        """Backward-compatible price lookup using the same pair selection."""
        metrics = await self._fetch_pair_metrics(rows, chain)
        return {key: self._number(value.get("price")) for key, value in metrics.items()}

    async def _fetch_market_caps(
        self,
        rows: List[Dict[str, Any]],
        chain: str,
    ) -> Dict[str, float]:
        """Return market cap from the same selected pair used for pricing."""
        metrics = await self._fetch_pair_metrics(rows, chain)
        return {key: self._number(value.get("market_cap")) for key, value in metrics.items()}

    async def _process_market_cap(
        self,
        row: Dict[str, Any],
        market_cap: float,
        current_price: float = 0.0,
    ):
        entry_mc = self._number(row.get("entry_market_cap"))
        if entry_mc <= 0 or market_cap <= 0:
            return

        pnl = ((market_cap - entry_mc) / entry_mc) * 100.0
        previous_highest_pnl = self._number(row.get("highest_pnl"))
        highest_mc = max(self._number(row.get("highest_market_cap")), market_cap)
        highest_pnl = max(previous_highest_pnl, pnl)
        old_milestone = self._number(row.get("last_milestone"))
        new_milestone = self._highest_reached(pnl)
        stored_milestone = max(old_milestone, new_milestone)

        self._update_row(
            signal_key=row["signal_key"],
            current_market_cap=market_cap,
            highest_market_cap=highest_mc,
            current_price=current_price,
            highest_price=max(self._number(row.get("highest_price")), current_price),
            highest_pnl=highest_pnl,
            last_milestone=stored_milestone,
        )

        if new_milestone > old_milestone:
            await self._send_update(
                row=row,
                current_market_cap=market_cap,
                current_price=current_price,
                pnl=pnl,
                milestone=new_milestone,
                highest_pnl=highest_pnl,
                drawdown=0.0,
                alert_type="milestone",
            )

        drawdown = max(0.0, highest_pnl - pnl)
        alerted_peak = self._number(row.get("drawdown_alerted_peak"))
        new_peak_since_alert = highest_pnl > alerted_peak + 0.1
        should_alert_drawdown = (
            highest_pnl >= self.drawdown_alert
            and drawdown >= self.drawdown_alert
            and new_peak_since_alert
        )

        if should_alert_drawdown:
            self._mark_drawdown_alert(row["signal_key"], highest_pnl)
            await self._send_update(
                row=row,
                current_market_cap=market_cap,
                current_price=current_price,
                pnl=pnl,
                milestone=stored_milestone,
                highest_pnl=highest_pnl,
                drawdown=drawdown,
                alert_type="drawdown",
            )

    async def _process_price(self, row: Dict[str, Any], price: float):
        """Legacy compatibility wrapper; MC remains the primary PNL metric."""
        if price <= 0:
            return
        market_cap = self._number(row.get("current_market_cap"))
        if market_cap > 0:
            await self._process_market_cap(row, market_cap, price)

    async def _send_update(
        self,
        row: Dict[str, Any],
        current_market_cap: float,
        current_price: float,
        pnl: float,
        milestone: float,
        highest_pnl: float,
        drawdown: float = 0.0,
        alert_type: str = "milestone",
    ):
        symbol = row["symbol"]

        chain = str(
            row["chain"]
        ).lower()

        chain_label = (
            "🟣 Solana"
            if chain == "solana"
            else "🔵 Base"
            if chain == "base"
            else f"⚪ {chain.title()}"
        )

        multiplier = 1 + (
            pnl / 100.0
        )

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

        pair_line = ""
        pair_address = str(
            row.get("pair_address", "")
            or ""
        ).strip()

        if pair_address:
            pair_line = (
                f"🔗 Pair: <code>"
                f"{self._escape(pair_address)}"
                f"</code>"
            )

        message = "\n".join(
            [
                title,
                "━━━━━━━━━━━━━━━━━━━━",
                f"🟢 <b>${self._escape(symbol)}</b>",
                chain_label,
                "",
                "💰 <b>MARKET CAP</b>",
                f"┗ Entry MC: <b>{self._format_money(row['entry_market_cap'])}</b>",
                f"┗ Current MC: <b>{self._format_money(current_market_cap)}</b>",
                "",
                "📊 <b>PNL</b>",
                f"┗ Current PNL: <b>{pnl:+.1f}%</b>",
                milestone_line,
                f"┗ Multiple: <b>{multiplier:.2f}X</b>",
                f"┗ Best PNL: <b>+{highest_pnl:.1f}%</b>",
                f"┗ Best MC: <b>{self._format_money(row.get('highest_market_cap'))}</b>",
                (
                    f"┗ Drawdown: <b>-{drawdown:.1f}%</b>"
                    if drawdown > 0
                    else ""
                ),
                "",
                f"📄 <code>{self._escape(row['address'])}</code>",
                pair_line,
                "",
                f"💵 Price: <b>{self._format_price(current_price)}</b>",
                "⚠️ <i>PNL is market-cap based; fees/slippage/taxes are not included.</i>",
            ]
        )

        # Remove intentionally empty lines caused by optional fields.
        message = "\n".join(
            line
            for line in message.splitlines()
            if line != ""
            or True
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
            print(
                f"❌ PNL Telegram error for "
                f"${symbol}: {exc}"
            )

    def get_tracked(
        self,
        address: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return tracked rows, optionally filtered by address or chain:address."""
        normalized = str(
            address or ""
        ).strip()

        query = """
            SELECT
                signal_key,
                chain,
                address,
                symbol,
                pair_address,
                pair_created,
                twitter_url,
                telegram_url,
                website_url,
                entry_market_cap,
                current_market_cap,
                highest_market_cap,
                entry_price,
                current_price,
                highest_price,
                highest_pnl,
                last_milestone,
                drawdown_alerted_peak,
                started_at,
                updated_at
            FROM pnl_tracking
        """

        params: tuple = ()

        if normalized:
            if ":" in normalized:
                chain, raw_address = normalized.split(
                    ":",
                    1,
                )

                query += (
                    " WHERE lower(chain)=lower(?) "
                    "AND lower(address)=lower(?)"
                )

                params = (
                    chain.strip(),
                    raw_address.strip(),
                )
            else:
                query += (
                    " WHERE lower(address)=lower(?)"
                )

                params = (
                    normalized,
                )

        query += (
            " ORDER BY updated_at DESC LIMIT ?"
        )

        params = (
            *params,
            self.max_tracked,
        )

        with self._lock:
            with self._db() as db:
                rows = db.execute(
                    query,
                    params,
                ).fetchall()

        columns = [
            "signal_key",
            "chain",
            "address",
            "symbol",
            "pair_address",
            "pair_created",
            "twitter_url",
            "telegram_url",
            "website_url",
            "entry_market_cap",
            "current_market_cap",
            "highest_market_cap",
            "entry_price",
            "current_price",
            "highest_price",
            "highest_pnl",
            "last_milestone",
            "drawdown_alerted_peak",
            "started_at",
            "updated_at",
        ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    def get_pnl_rows(
        self,
        mode: str = "all",
    ) -> List[Dict[str, Any]]:
        """Return tracked rows using useful PNL filters for Telegram."""
        rows = self.get_tracked(None)

        mode = str(
            mode or "all"
        ).strip().lower()

        if mode in {
            "",
            "all",
            "summary",
        }:
            return rows

        if mode in {
            "winner",
            "winners",
            "profit",
            "profits",
            "green",
        }:
            return [
                row
                for row in rows
                if self._row_pnl(row) > 0
            ]

        if mode in {
            "loser",
            "losers",
            "loss",
            "losses",
            "red",
        }:
            return [
                row
                for row in rows
                if self._row_pnl(row) < 0
            ]

        if mode in {
            "breakeven",
            "flat",
            "zero",
        }:
            return [
                row
                for row in rows
                if abs(
                    self._row_pnl(row)
                ) < 0.01
            ]

        multiplier_targets = {
            "2x": 100.0,
            "5x": 400.0,
            "10x": 900.0,
        }

        if mode in multiplier_targets:
            minimum = multiplier_targets[mode]

            return [
                row
                for row in rows
                if self._row_pnl(row) >= minimum
            ]

        if mode in {
            "best",
            "top",
            "gainers",
        }:
            return sorted(
                rows,
                key=self._row_pnl,
                reverse=True,
            )

        if mode in {
            "worst",
            "bottom",
            "losing",
        }:
            return sorted(
                rows,
                key=self._row_pnl,
            )

        return []

    def get_pnl_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for all tracked positions."""
        rows = self.get_tracked(None)

        pnls = [
            self._row_pnl(row)
            for row in rows
        ]

        winners = [
            value
            for value in pnls
            if value > 0
        ]

        losers = [
            value
            for value in pnls
            if value < 0
        ]

        return {
            "total": len(rows),
            "winners": len(winners),
            "losers": len(losers),
            "flat": (
                len(pnls)
                - len(winners)
                - len(losers)
            ),
            "average_pnl": (
                sum(pnls) / len(pnls)
                if pnls
                else 0.0
            ),
            "best_pnl": (
                max(pnls)
                if pnls
                else 0.0
            ),
            "worst_pnl": (
                min(pnls)
                if pnls
                else 0.0
            ),
            "two_x": sum(
                1
                for value in pnls
                if value >= 100
            ),
            "five_x": sum(
                1
                for value in pnls
                if value >= 400
            ),
            "ten_x": sum(
                1
                for value in pnls
                if value >= 900
            ),
        }

    def _highest_reached(self, pnl: float) -> float:
        """Return the highest configured milestone reached by this MC PNL."""
        reached = 0.0
        for milestone in self.milestones:
            if pnl >= milestone:
                reached = milestone
            else:
                break
        return reached

    @staticmethod
    def _row_pnl(row: Dict[str, Any]) -> float:
        entry = PNLTracker._number(row.get("entry_market_cap"))
        current = PNLTracker._number(row.get("current_market_cap"))
        if entry <= 0:
            return 0.0
        return ((current - entry) / entry) * 100.0

    @staticmethod
    def format_pnl_summary(
        rows: List[Dict[str, Any]],
    ) -> str:
        """Format a compact professional PNL summary."""
        if not rows:
            return (
                "ℹ️ Babu token da ya dace "
                "da wannan PNL filter."
            )

        stats = {
            "total": len(rows),
            "winners": sum(
                1
                for row in rows
                if PNLTracker._row_pnl(row) > 0
            ),
            "losers": sum(
                1
                for row in rows
                if PNLTracker._row_pnl(row) < 0
            ),
        }

        ordered = sorted(
            rows,
            key=PNLTracker._row_pnl,
            reverse=True,
        )

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
            multiple = 1.0 + (
                pnl / 100.0
            )

            symbol = PNLTracker._escape(
                row.get(
                    "symbol",
                    "N/A",
                )
            )

            lines.append(
                f"🟢 ${symbol}  "
                f"<b>{pnl:+.1f}%</b>  "
                f"({multiple:.2f}X)"
            )

        lines.extend(
            [
                "",
                "📉 <b>BIGGEST LOSERS</b>",
            ]
        )

        for row in sorted(
            rows,
            key=PNLTracker._row_pnl,
        )[:5]:
            pnl = PNLTracker._row_pnl(row)
            multiple = 1.0 + (
                pnl / 100.0
            )

            symbol = PNLTracker._escape(
                row.get(
                    "symbol",
                    "N/A",
                )
            )

            lines.append(
                f"🔴 ${symbol}  "
                f"<b>{pnl:+.1f}%</b>  "
                f"({multiple:.2f}X)"
            )

        lines.extend(
            [
                "",
                "🎯 <b>MULTIPLES</b>",
                "┗ 2X+: <b>"
                f"{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 100)}"
                "</b>",
                "┗ 5X+: <b>"
                f"{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 400)}"
                "</b>",
                "┗ 10X+: <b>"
                f"{sum(1 for row in rows if PNLTracker._row_pnl(row) >= 900)}"
                "</b>",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def format_manual_pnl(row: Dict[str, Any]) -> str:
        """Format one tracked PNL row using market cap as the primary metric."""
        entry_mc = PNLTracker._number(row.get("entry_market_cap"))
        current_mc = PNLTracker._number(row.get("current_market_cap"))
        highest_mc = PNLTracker._number(row.get("highest_market_cap"))
        highest_pnl = PNLTracker._number(row.get("highest_pnl"))
        current_price = PNLTracker._number(row.get("current_price"))
        pnl = PNLTracker._row_pnl(row)
        multiple = 1.0 + (pnl / 100.0)
        change = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        chain = str(row.get("chain", "")).lower()
        chain_label = (
            "🟣 Solana" if chain == "solana" else
            "🔵 Base" if chain == "base" else
            f"⚪ {chain.title()}"
        )
        milestone = PNLTracker._number(row.get("last_milestone"))
        drawdown = max(0.0, highest_pnl - pnl)
        pair_address = str(row.get("pair_address", "") or "").strip()
        # AGE is shown by the signal engine; /pnl intentionally does not
        # reintroduce the old Created timestamp.
        twitter_url = str(row.get("twitter_url", "") or "").strip()
        telegram_url = str(row.get("telegram_url", "") or "").strip()
        website_url = str(row.get("website_url", "") or "").strip()
        lines = [
            f"{change} <b>${PNLTracker._escape(row.get('symbol', 'N/A'))}</b>",
            chain_label,
            f"💰 Entry MC: <b>{PNLTracker._format_money(entry_mc)}</b>",
            f"📍 Current MC: <b>{PNLTracker._format_money(current_mc)}</b>",
            f"📊 MC PNL: <b>{pnl:+.1f}%</b>",
            f"🚀 Multiple: <b>{multiple:.2f}X</b>",
            f"🏆 Best MC: <b>{PNLTracker._format_money(highest_mc)}</b>",
            f"🏆 Best PNL: <b>{highest_pnl:+.1f}%</b>",
            f"💵 Current Price: <b>{PNLTracker._format_price(current_price)}</b>",
            "🎯 Last Milestone: <b>" + (f"+{milestone:.0f}%" if milestone > 0 else "None") + "</b>",
        ]
        social_lines = []
        if twitter_url:
            social_lines.append(f'<a href="{PNLTracker._escape(twitter_url)}">𝕏 X</a>')
        if telegram_url:
            social_lines.append(f'<a href="{PNLTracker._escape(telegram_url)}">Telegram</a>')
        if website_url:
            social_lines.append(f'<a href="{PNLTracker._escape(website_url)}">Website</a>')
        if social_lines:
            lines.append("🔗 <b>Socials:</b> " + " • ".join(social_lines))
        if drawdown > 0.01:
            lines.append(f"📉 Drawdown from best: <b>-{drawdown:.1f}%</b>")
        lines.append(f"📄 <code>{PNLTracker._escape(row.get('address', ''))}</code>")
        if pair_address:
            lines.append(f"🔗 Pair: <code>{PNLTracker._escape(pair_address)}</code>")
        return "\n".join(lines)

    def _load_active(
        self,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            with self._db() as db:
                rows = db.execute(
                    """
                    SELECT
                        signal_key,
                        chain,
                        address,
                        symbol,
                        pair_address,
                        entry_market_cap,
                        current_market_cap,
                        highest_market_cap,
                        entry_price,
                        current_price,
                        highest_price,
                        highest_pnl,
                        last_milestone,
                        drawdown_alerted_peak,
                        started_at,
                        updated_at
                    FROM pnl_tracking
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (self.max_tracked,),
                ).fetchall()

        columns = [
            "signal_key",
            "chain",
            "address",
            "symbol",
            "pair_address",
            "entry_market_cap",
            "current_market_cap",
            "highest_market_cap",
            "entry_price",
            "current_price",
            "highest_price",
            "highest_pnl",
            "last_milestone",
            "drawdown_alerted_peak",
            "started_at",
            "updated_at",
        ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    def _update_row(
        self,
        signal_key: str,
        current_market_cap: float,
        highest_market_cap: float,
        current_price: float,
        highest_price: float,
        highest_pnl: float,
        last_milestone: float,
    ):
        with self._lock:
            with self._db() as db:
                db.execute(
                    """
                    UPDATE pnl_tracking
                    SET
                        current_market_cap=?,
                        highest_market_cap=?,
                        current_price=?,
                        highest_price=?,
                        highest_pnl=?,
                        last_milestone=?,
                        updated_at=?
                    WHERE signal_key=?
                    """,
                    (
                        current_market_cap,
                        highest_market_cap,
                        current_price,
                        highest_price,
                        highest_pnl,
                        last_milestone,
                        time.time(),
                        signal_key,
                    ),
                )

    def _mark_drawdown_alert(
        self,
        signal_key: str,
        peak_pnl: float,
    ):
        with self._lock:
            with self._db() as db:
                db.execute(
                    """
                    UPDATE pnl_tracking
                    SET drawdown_alerted_peak=?
                    WHERE signal_key=?
                    """,
                    (
                        peak_pnl,
                        signal_key,
                    ),
                )

    @staticmethod
    def _signal_key(
        token: Dict[str, Any],
    ) -> str:
        chain = str(
            token.get("chain", "")
            or ""
        ).lower().strip()

        address = str(
            token.get("address", "")
            or ""
        ).strip()

        if not chain or not address:
            return ""

        return f"{chain}:{address}"

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(
                value or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _escape(value: Any) -> str:
        text = str(
            value or ""
        )

        return (
            text.replace(
                "&",
                "&amp;",
            )
            .replace(
                "<",
                "&lt;",
            )
            .replace(
                ">",
                "&gt;",
            )
        )

    @staticmethod
    def _format_money(value: float) -> str:
        value = float(value or 0)
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:.1f}K"
        return f"${value:,.0f}"

    @staticmethod
    def _format_price(
        value: float,
    ) -> str:
        value = float(
            value or 0
        )

        if value >= 1:
            return (
                f"${value:,.6f}"
                .rstrip("0")
                .rstrip(".")
            )

        if value >= 0.01:
            return (
                f"${value:.8f}"
                .rstrip("0")
                .rstrip(".")
            )

        return (
            f"${value:.12f}"
            .rstrip("0")
            .rstrip(".")
        )
