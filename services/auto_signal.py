"""
SALIM SAUKI DATA
AUTO TELEGRAM SIGNAL ENGINE V3

Features:
    - Automatic Solana token scanning
    - Final signal filtering
    - Recommendation filtering
    - Security filtering
    - Candidate ranking
    - Best-signal-first delivery
    - Duplicate protection
    - Cooldown protection
    - Signal history
    - Telegram delivery
    - Clean signal formatting

NOT FINANCIAL ADVICE.
"""

import asyncio
import time
from typing import Any, Dict, List, Set, Tuple

from services.scanner import TokenScanner


class AutoSignalEngine:

    # =========================================================
    # DEFAULT SETTINGS
    # =========================================================

    DEFAULT_INTERVAL = 60

    DEFAULT_COOLDOWN = 3600

    # Maximum number of signals allowed from one scan.
    DEFAULT_MAX_SIGNALS_PER_SCAN = 3

    # Minimum recommendation score.
    MIN_RECOMMENDATION_SCORE = 75

    # Minimum final score.
    MIN_FINAL_SCORE = 75

    # Minimum security score.
    MIN_SECURITY_SCORE = 90

    # Keep only recent history in memory.
    MAX_HISTORY = 5000

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        bot,
        chat_id,
        interval: int = DEFAULT_INTERVAL,
        cooldown: int = DEFAULT_COOLDOWN,
        max_signals_per_scan: int = DEFAULT_MAX_SIGNALS_PER_SCAN,
    ):

        self.bot = bot

        self.chat_id = chat_id

        self.interval = max(
            10,
            int(
                interval
                or self.DEFAULT_INTERVAL
            ),
        )

        self.cooldown = max(
            60,
            int(
                cooldown
                or self.DEFAULT_COOLDOWN
            ),
        )

        self.max_signals_per_scan = max(
            1,
            int(
                max_signals_per_scan
                or self.DEFAULT_MAX_SIGNALS_PER_SCAN
            ),
        )

        self.scanner = TokenScanner()

        # =====================================================
        # SENT CONTRACTS
        # =====================================================

        self.sent_contracts: Set[str] = set()

        # =====================================================
        # SIGNAL HISTORY
        #
        # address -> timestamp
        # =====================================================

        self.signal_history: Dict[str, float] = {}

        # =====================================================
        # STATE
        # =====================================================

        self.running = False

        # =====================================================
        # STATISTICS
        # =====================================================

        self.scan_count = 0

        self.signals_sent = 0

        self.duplicates_skipped = 0

        self.cooldown_skipped = 0

        self.filtered_out = 0

        self.telegram_errors = 0

    # =========================================================
    # START
    # =========================================================

    async def start(self):

        if self.running:

            print(
                "⚠️ Auto Signal Engine already running."
            )

            return

        self.running = True

        print(
            "========================================"
        )

        print(
            "💎 SALIM SAUKI DATA — AUTO SIGNAL"
        )

        print(
            "========================================"
        )

        print(
            f"📡 Chat ID: {self.chat_id}"
        )

        print(
            f"⏱️ Scan interval: {self.interval}s"
        )

        print(
            f"🕒 Signal cooldown: {self.cooldown}s"
        )

        print(
            f"🏆 Max signals/scan: "
            f"{self.max_signals_per_scan}"
        )

        print(
            "🚀 AUTO SIGNAL ENGINE V3 STARTED"
        )

        while self.running:

            started_at = time.time()

            try:

                await self.scan_once()

            except asyncio.CancelledError:

                self.running = False

                print(
                    "🛑 Auto Signal Engine cancelled."
                )

                raise

            except Exception as exc:

                print(
                    f"❌ Auto signal error: {exc}"
                )

            elapsed = (
                time.time()
                - started_at
            )

            sleep_time = max(
                1,
                self.interval - elapsed,
            )

            if self.running:

                await asyncio.sleep(
                    sleep_time
                )

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if not self.running:

            return

        self.running = False

        print(
            "🛑 SALIM SAUKI DATA — "
            "AUTO SIGNAL ENGINE STOPPED"
        )

        print(
            f"📊 Scans: {self.scan_count}"
        )

        print(
            f"🚀 Signals sent: {self.signals_sent}"
        )

        print(
            f"⏭️ Duplicates: "
            f"{self.duplicates_skipped}"
        )

        print(
            f"⏳ Cooldown skipped: "
            f"{self.cooldown_skipped}"
        )

        print(
            f"🚫 Filtered: "
            f"{self.filtered_out}"
        )

    # =========================================================
    # SCAN ONCE
    # =========================================================

    async def scan_once(self):

        self.scan_count += 1

        print("")

        print(
            "🔎 Auto Signal: scanning..."
        )

        try:

            results = await self.scanner.scan(
                "sol"
            )

        except Exception as exc:

            print(
                f"❌ Scanner error: {exc}"
            )

            return

        if not results:

            print(
                "📊 Candidates found: 0"
            )

            return

        print(
            f"📊 Candidates found: "
            f"{len(results)}"
        )

        # =====================================================
        # CLEAN HISTORY
        # =====================================================

        self._cleanup_history()

        # =====================================================
        # BUILD CURRENT CANDIDATES
        # =====================================================

        candidates: List[
            Tuple[
                Tuple,
                Dict[str, Any]
            ]
        ] = []

        current_scan: Set[str] = set()

        for token in results:

            if not isinstance(
                token,
                dict,
            ):

                self.filtered_out += 1

                continue

            # -------------------------------------------------
            # BASIC SIGNAL FILTER
            # -------------------------------------------------

            if not self._is_signal(
                token
            ):

                self.filtered_out += 1

                continue

            # -------------------------------------------------
            # CONTRACT
            # -------------------------------------------------

            address = str(
                token.get(
                    "address",
                    "",
                )
                or ""
            ).strip()

            if not address:

                self.filtered_out += 1

                continue

            # -------------------------------------------------
            # CURRENT SCAN DUPLICATE
            # -------------------------------------------------

            if address in current_scan:

                self.duplicates_skipped += 1

                continue

            current_scan.add(
                address
            )

            # -------------------------------------------------
            # COOLDOWN
            # -------------------------------------------------

            if self._is_on_cooldown(
                address
            ):

                self.cooldown_skipped += 1

                print(
                    f"⏳ Cooldown active: "
                    f"${token.get('symbol', 'N/A')}"
                )

                continue

            # -------------------------------------------------
            # RANK
            # -------------------------------------------------

            ranking = self._ranking_key(
                token
            )

            candidates.append(
                (
                    ranking,
                    token,
                )
            )

        # =====================================================
        # NO VALID CANDIDATES
        # =====================================================

        if not candidates:

            print(
                "🏆 No new signal candidates."
            )

            return

        # =====================================================
        # TRUE RANKING
        # =====================================================

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        print(
            f"🏆 Ranked candidates: "
            f"{len(candidates)}"
        )

        # =====================================================
        # SEND BEST SIGNALS FIRST
        # =====================================================

        sent_this_scan = 0

        for ranking, token in candidates:

            if (
                sent_this_scan
                >= self.max_signals_per_scan
            ):

                break

            address = str(
                token.get(
                    "address",
                    "",
                )
                or ""
            ).strip()

            symbol = str(
                token.get(
                    "symbol",
                    "N/A",
                )
                or "N/A"
            )

            print(
                "🏆 Candidate:",
                f"${symbol}",
                f"REC={self._int(token.get('recommendation_score'))}",
                f"FINAL={self._int(token.get('final_score'))}",
                f"GEM={self._int(token.get('gem_score'))}",
                f"AI={self._int(token.get('ai_score'))}",
            )

            message = self.format_signal(
                token
            )

            try:

                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    disable_web_page_preview=True,
                )

            except Exception as exc:

                self.telegram_errors += 1

                print(
                    f"❌ Telegram send error "
                    f"for ${symbol}: {exc}"
                )

                continue

            # -------------------------------------------------
            # MARK SENT ONLY AFTER SUCCESS
            # -------------------------------------------------

            now = time.time()

            self.sent_contracts.add(
                address
            )

            self.signal_history[
                address
            ] = now

            self.signals_sent += 1

            sent_this_scan += 1

            print(
                f"🚀 SIGNAL SENT: "
                f"${symbol} "
                f"{address}"
            )

        # =====================================================
        # HISTORY LIMIT
        # =====================================================

        self._limit_history()

        print(
            f"📤 Signals sent this scan: "
            f"{sent_this_scan}"
        )

    # =========================================================
    # SIGNAL FILTER
    # =========================================================

    @classmethod
    def _is_signal(
        cls,
        token: Dict[str, Any],
    ) -> bool:

        if not isinstance(
            token,
            dict,
        ):

            return False

        # =====================================================
        # FINAL ENGINE
        # =====================================================

        if not token.get(
            "final_should_signal",
            False,
        ):

            return False

        # =====================================================
        # RECOMMENDATION
        # =====================================================

        if not token.get(
            "is_recommended",
            False,
        ):

            return False

        # =====================================================
        # SECURITY
        # =====================================================

        if not token.get(
            "security_should_pass",
            False,
        ):

            return False

        security_score = cls._number(
            token.get(
                "security_score",
                0,
            )
        )

        if security_score < cls.MIN_SECURITY_SCORE:

            return False

        # =====================================================
        # RECOMMENDATION SCORE
        # =====================================================

        recommendation_score = cls._number(
            token.get(
                "recommendation_score",
                0,
            )
        )

        if (
            recommendation_score
            < cls.MIN_RECOMMENDATION_SCORE
        ):

            return False

        # =====================================================
        # FINAL SCORE
        # =====================================================

        final_score = cls._number(
            token.get(
                "final_score",
                0,
            )
        )

        if final_score < cls.MIN_FINAL_SCORE:

            return False

        return True

    # =========================================================
    # RANKING
    # =========================================================

    @classmethod
    def _ranking_key(
        cls,
        token: Dict[str, Any],
    ) -> Tuple:

        recommendation_score = cls._number(
            token.get(
                "recommendation_score",
                0,
            )
        )

        final_score = cls._number(
            token.get(
                "final_score",
                0,
            )
        )

        gem_score = cls._number(
            token.get(
                "gem_score",
                0,
            )
        )

        ai_score = cls._number(
            token.get(
                "ai_score",
                0,
            )
        )

        security_score = cls._number(
            token.get(
                "security_score",
                0,
            )
        )

        buy_ratio = cls._number(
            token.get(
                "buy_ratio",
                0,
            )
        )

        liquidity_ratio = cls._number(
            token.get(
                "liquidity_ratio",
                0,
            )
        )

        volume_ratio = cls._number(
            token.get(
                "volume_ratio",
                0,
            )
        )

        # Highest priority:
        #
        # 1. recommendation
        # 2. final score
        # 3. gem score
        # 4. AI score
        # 5. security
        # 6. buy pressure
        # 7. liquidity quality
        # 8. volume activity

        return (
            recommendation_score,
            final_score,
            gem_score,
            ai_score,
            security_score,
            buy_ratio,
            liquidity_ratio,
            volume_ratio,
        )

    # =========================================================
    # COOLDOWN CHECK
    # =========================================================

    def _is_on_cooldown(
        self,
        address: str,
    ) -> bool:

        if not address:

            return False

        last_sent = self.signal_history.get(
            address
        )

        if last_sent is None:

            return False

        elapsed = (
            time.time()
            - last_sent
        )

        return elapsed < self.cooldown

    # =========================================================
    # CLEAN HISTORY
    # =========================================================

    def _cleanup_history(self):

        if not self.signal_history:

            return

        now = time.time()

        expired = []

        for (
            address,
            timestamp,
        ) in list(
            self.signal_history.items()
        ):

            if (
                now - timestamp
            ) >= self.cooldown:

                expired.append(
                    address
                )

        for address in expired:

            self.signal_history.pop(
                address,
                None,
            )

            self.sent_contracts.discard(
                address
            )

    # =========================================================
    # LIMIT HISTORY
    # =========================================================

    def _limit_history(self):

        if (
            len(self.signal_history)
            <= self.MAX_HISTORY
        ):

            return

        sorted_history = sorted(
            self.signal_history.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        keep = sorted_history[
            :self.MAX_HISTORY
        ]

        self.signal_history = dict(
            keep
        )

        self.sent_contracts = set(
            self.signal_history.keys()
        )

    # =========================================================
    # NUMBER
    # =========================================================

    @staticmethod
    def _number(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:

            if value is None:

                return default

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # =========================================================
    # INT
    # =========================================================

    @classmethod
    def _int(
        cls,
        value: Any,
        default: int = 0,
    ) -> int:

        try:

            return int(
                cls._number(
                    value,
                    default,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # =========================================================
    # FORMAT SIGNAL
    # =========================================================

    @classmethod
    def format_signal(
        cls,
        token: Dict[str, Any],
    ) -> str:

        symbol = str(
            token.get(
                "symbol",
                "N/A",
            )
            or "N/A"
        )

        name = str(
            token.get(
                "name",
                "Unknown",
            )
            or "Unknown"
        )

        chain_name = str(
            token.get(
                "chain_name",
                "🟣 Solana",
            )
            or "🟣 Solana"
        )

        final_score = cls._int(
            token.get(
                "final_score",
                0,
            )
        )

        ai_score = cls._int(
            token.get(
                "ai_score",
                0,
            )
        )

        gem_score = cls._int(
            token.get(
                "gem_score",
                0,
            )
        )

        security_score = cls._int(
            token.get(
                "security_score",
                0,
            )
        )

        recommendation = str(
            token.get(
                "recommendation",
                "🚀 BUY",
            )
            or "🚀 BUY"
        )

        recommendation_score = cls._int(
            token.get(
                "recommendation_score",
                0,
            )
        )

        confidence = cls._int(
            token.get(
                "recommendation_confidence",
                token.get(
                    "confidence",
                    0,
                ),
            )
        )

        risk = str(
            token.get(
                "recommendation_risk",
                token.get(
                    "risk_level",
                    "⚪ UNKNOWN",
                ),
            )
            or "⚪ UNKNOWN"
        )

        marketcap = cls._number(
            token.get(
                "marketcap",
                0,
            )
        )

        liquidity = cls._number(
            token.get(
                "liquidity",
                0,
            )
        )

        volume = cls._number(
            token.get(
                "volume24h",
                0,
            )
        )

        total_txns = cls._int(
            token.get(
                "total_txns",
                0,
            )
        )

        buy_ratio = cls._number(
            token.get(
                "buy_ratio",
                0,
            )
        )

        price_change = cls._number(
            token.get(
                "price_change_24h",
                0,
            )
        )

        positive = token.get(
            "recommendation_positive_reasons",
            [],
        ) or []

        final_reasons = token.get(
            "final_reasons",
            [],
        ) or []

        address = str(
            token.get(
                "address",
                "",
            )
            or ""
        )

        # =====================================================
        # MESSAGE
        # =====================================================

        lines = [

            "🧠 SALIM SAUKI DATA",

            "💎 AUTO GEM SIGNAL",

            "",

            f"🚀 {recommendation}",

            "",

            f"🪙 ${symbol} — {name}",

            f"⛓️ Chain: {chain_name}",

            "",

            "📊 MARKET DATA",

            f"💰 MC: ${marketcap:,.0f}",

            f"💧 LIQ: ${liquidity:,.0f}",

            f"📈 VOL 24H: ${volume:,.0f}",

            f"🔄 TXNS: {total_txns}",

            f"🟢 BUY RATIO: "
            f"{buy_ratio * 100:.1f}%",

            f"📊 24H CHANGE: "
            f"{price_change:.2f}%",

            "",

            "🧠 AI ANALYSIS",

            f"🤖 AI: {ai_score}/100",

            f"💎 GEM: {gem_score}/100",

            f"🔐 SECURITY: "
            f"{security_score}/100",

            f"🎯 FINAL: "
            f"{final_score}/100",

            "",

            "🤖 RECOMMENDATION",

            f"{recommendation}",

            f"📊 Score: "
            f"{recommendation_score}/100",

            f"🎯 Confidence: "
            f"{confidence}%",

            f"🛡 Risk: {risk}",
        ]

        # =====================================================
        # POSITIVE FACTORS
        # =====================================================

        if positive:

            lines.extend(
                [
                    "",
                    "✅ POSITIVE FACTORS",
                ]
            )

            for reason in positive[:8]:

                lines.append(
                    f"• {reason}"
                )

        # =====================================================
        # FINAL REASONS
        # =====================================================

        if final_reasons:

            lines.extend(
                [
                    "",
                    "📋 FINAL REASONS",
                ]
            )

            for reason in final_reasons[:8]:

                lines.append(
                    f"• {reason}"
                )

        # =====================================================
        # CONTRACT
        # =====================================================

        lines.extend(
            [
                "",
                "📄 CONTRACT ADDRESS",
                address,
                "",
                "━━━━━━━━━━━━━━━━━━━━",
                "⚠️ Wannan signal ba guarantee bane.",
                "DYOR kafin kowane trade.",
            ]
        )

        return "\n".join(
            lines
        )


# =============================================================
# SIMPLE TEST
# =============================================================

async def test_engine():

    class FakeBot:

        async def send_message(
            self,
            chat_id,
            text,
            disable_web_page_preview=True,
        ):

            print(
                "=" * 70
            )

            print(
                "TELEGRAM TEST MESSAGE"
            )

            print(
                "=" * 70
            )

            print(
                text
            )

            print(
                "=" * 70
            )

    engine = AutoSignalEngine(
        bot=FakeBot(),
        chat_id="TEST",
        interval=60,
        cooldown=3600,
        max_signals_per_scan=3,
    )

    await engine.scan_once()


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    asyncio.run(
        test_engine()
    )
