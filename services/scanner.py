from typing import Any, Dict, List

from services.dexscreener import DexScreener
from services.security import SecurityChecker
from services.final_signal import FinalSignalEngine

from ai.scoring import AIScoring
from ai.gem_detector import GemDetector
from ai.recommendation import RecommendationEngine


class TokenScanner:

    SUPPORTED_CHAINS = {
        "solana": "🟣 Solana",
    }

    # =========================================================
    # SMALL-CAP GEM FILTERS
    # =========================================================

    MIN_MARKETCAP = 10_000
    MAX_MARKETCAP = 5_000_000

    MIN_LIQUIDITY = 10_000
    MIN_VOLUME_24H = 5_000
    MIN_TXNS = 20

    MIN_BUY_RATIO = 0.50

    # =========================================================
    # DISCOVERY
    # =========================================================

    DISCOVERY_QUERIES = [
        "sol",
        "pump",
        "meme",
        "ai",
        "dog",
        "cat",
        "inu",
        "pepe",
        "moon",
        "trump",
    ]

    # =========================================================
    # V7 RANKING PRIORITY
    # =========================================================

    SIGNAL_PRIORITY = {
        "🔥 STRONG GEM": 5,
        "🚀 GEM SIGNAL": 4,
        "👀 EARLY GEM": 3,
        "🟡 WATCH": 2,
        "⛔ NO SIGNAL": 0,
    }

    STATUS_PRIORITY = {
        "STRONG GEM": 5,
        "GEM SIGNAL": 4,
        "EARLY GEM": 3,
        "WATCH": 2,
        "REJECT": 0,
    }

    def __init__(self):

        self.dex = DexScreener()

        self.security = SecurityChecker()

        self.gem_detector = GemDetector()

    # =========================================================
    # SCAN
    # =========================================================

    async def scan(
        self,
        query="sol",
    ):

        # -----------------------------------------------------
        # DISCOVERY
        # -----------------------------------------------------

        queries = list(
            self.DISCOVERY_QUERIES
        )

        if query:

            query = str(
                query
            ).strip()

            if (
                query
                and query not in queries
            ):

                queries.insert(
                    0,
                    query,
                )

        try:

            pairs = await self.dex.discover_solana(
                queries
            )

        except Exception as exc:

            print(
                f"❌ Solana discovery failed: {exc}"
            )

            return []

        print(
            f"📊 Raw Solana candidates: "
            f"{len(pairs)}"
        )

        results = []

        seen = set()

        # =====================================================
        # PROCESS PAIRS
        # =====================================================

        for pair in pairs:

            if not isinstance(
                pair,
                dict,
            ):

                continue

            chain = str(
                pair.get(
                    "chainId",
                    "",
                )
            ).lower()

            if chain != "solana":

                continue

            base = pair.get(
                "baseToken"
            ) or {}

            liquidity = pair.get(
                "liquidity"
            ) or {}

            volume = pair.get(
                "volume"
            ) or {}

            txns = pair.get(
                "txns"
            ) or {}

            h24 = txns.get(
                "h24"
            ) or {}

            price_change = pair.get(
                "priceChange"
            ) or {}

            address = str(
                base.get(
                    "address",
                    "",
                )
                or ""
            ).strip()

            if not address:

                continue

            # -------------------------------------------------
            # TOKEN DEDUPLICATION
            # -------------------------------------------------

            if address in seen:

                continue

            seen.add(
                address
            )

            # -------------------------------------------------
            # MARKET DATA
            # -------------------------------------------------

            marketcap = self._number(
                pair.get(
                    "marketCap"
                )
                or pair.get(
                    "fdv"
                )
                or 0
            )

            liquidity_usd = self._number(
                liquidity.get(
                    "usd"
                )
                or 0
            )

            volume_24h = self._number(
                volume.get(
                    "h24"
                )
                or 0
            )

            buys = self._number(
                h24.get(
                    "buys"
                )
                or 0
            )

            sells = self._number(
                h24.get(
                    "sells"
                )
                or 0
            )

            total_txns = (
                buys + sells
            )

            buy_ratio = 0.0

            if total_txns > 0:

                buy_ratio = (
                    buys / total_txns
                )

            # =================================================
            # HARD MARKET FILTER
            # =================================================

            if marketcap < self.MIN_MARKETCAP:
                continue

            if marketcap > self.MAX_MARKETCAP:
                continue

            if liquidity_usd < self.MIN_LIQUIDITY:
                continue

            if volume_24h < self.MIN_VOLUME_24H:
                continue

            if total_txns < self.MIN_TXNS:
                continue

            if buy_ratio < self.MIN_BUY_RATIO:
                continue

            # =================================================
            # TOKEN OBJECT
            # =================================================

            token = {

                "name": base.get(
                    "name",
                    "Unknown",
                ),

                "symbol": base.get(
                    "symbol",
                    "N/A",
                ),

                "address": address,

                "chain": chain,

                "chain_name":
                    self.SUPPORTED_CHAINS[
                        chain
                    ],

                "price": pair.get(
                    "priceUsd"
                ) or 0,

                "liquidity":
                    liquidity_usd,

                "volume24h":
                    volume_24h,

                "marketcap":
                    marketcap,

                "fdv": pair.get(
                    "fdv"
                ) or 0,

                "dex": pair.get(
                    "dexId"
                ),

                "pair": pair.get(
                    "pairAddress"
                ),

                "pair_created":
                    pair.get(
                        "pairCreatedAt"
                    ),

                "buys24h": int(
                    buys
                ),

                "sells24h": int(
                    sells
                ),

                "total_txns": int(
                    total_txns
                ),

                "buy_ratio":
                    buy_ratio,

                "price_change_24h":
                    self._number(
                        price_change.get(
                            "h24"
                        )
                        or 0
                    ),

                "url": pair.get(
                    "url"
                ),

                "quote_token":
                    pair.get(
                        "quoteToken"
                    ) or {},
            }

            # =================================================
            # AI SCORING
            # =================================================

            try:

                ai = AIScoring.calculate(
                    token
                )

            except Exception as exc:

                print(
                    f"AI scoring error "
                    f"for {address}: {exc}"
                )

                ai = {
                    "score": 0,
                    "grade": "F",
                    "signal": "🔴 AVOID",
                }

            token["ai_score"] = ai.get(
                "score",
                0,
            )

            token["ai_grade"] = ai.get(
                "grade",
                "N/A",
            )

            token["signal"] = ai.get(
                "signal",
                "⛔ NO SIGNAL",
            )

            # =================================================
            # GEM DETECTOR
            # =================================================

            try:

                gem = self.gem_detector.analyze(
                    token
                )

            except Exception as exc:

                print(
                    f"Gem detector error "
                    f"for {address}: {exc}"
                )

                gem = {
                    "gem_score": 0,
                    "gem_level": "🔴 REJECT",
                    "signal": "⛔ NO SIGNAL",
                    "should_signal": False,
                    "gem_reasons": [
                        "GEM DETECTOR ERROR"
                    ],
                    "liquidity_ratio": 0,
                    "volume_ratio": 0,
                    "buy_ratio": buy_ratio,
                    "total_txns": int(total_txns),
                }

            token["gem_score"] = gem.get(
                "gem_score",
                0,
            )

            token["gem_level"] = gem.get(
                "gem_level",
                "🔴 REJECT",
            )

            token["gem_signal"] = gem.get(
                "signal",
                "⛔ NO SIGNAL",
            )

            token["gem_should_signal"] = gem.get(
                "should_signal",
                False,
            )

            token["gem_reasons"] = gem.get(
                "gem_reasons",
                gem.get(
                    "reasons",
                    [],
                ),
            )

            token["liquidity_ratio"] = gem.get(
                "liquidity_ratio",
                0,
            )

            token["volume_ratio"] = gem.get(
                "volume_ratio",
                0,
            )

            token["buy_ratio"] = gem.get(
                "buy_ratio",
                buy_ratio,
            )

            token["total_txns"] = gem.get(
                "total_txns",
                int(total_txns),
            )

            # =================================================
            # SECURITY
            # =================================================

            try:

                security = await self.security.check(
                    token
                )

            except Exception as exc:

                print(
                    f"Security error for "
                    f"{address}: {exc}"
                )

                security = {

                    "security_score": 0,

                    "security_status":
                        "RPC ERROR",

                    "should_pass": False,

                    "mint_authority": None,

                    "freeze_authority": None,

                    "mint_authority_enabled":
                        None,

                    "freeze_authority_enabled":
                        None,

                    "supply": None,

                    "decimals": None,

                    "security_reasons": [
                        "SECURITY CHECK ERROR"
                    ],
                }

            # =================================================
            # SECURITY DATA
            # =================================================

            token["security_score"] = security.get(
                "security_score",
                0,
            )

            token["security_status"] = security.get(
                "security_status",
                "UNKNOWN",
            )

            token["security_should_pass"] = security.get(
                "should_pass",
                False,
            )

            token["mint_authority"] = security.get(
                "mint_authority"
            )

            token["freeze_authority"] = security.get(
                "freeze_authority"
            )

            token["mint_authority_enabled"] = security.get(
                "mint_authority_enabled"
            )

            token["freeze_authority_enabled"] = security.get(
                "freeze_authority_enabled"
            )

            token["supply"] = security.get(
                "supply"
            )

            token["decimals"] = security.get(
                "decimals"
            )

            token["security_reasons"] = security.get(
                "security_reasons",
                [],
            )

            # =================================================
            # FINAL SIGNAL
            # =================================================

            try:

                final = FinalSignalEngine.evaluate(
                    token,
                    security,
                )

            except Exception as exc:

                print(
                    f"Final signal error "
                    f"for {address}: {exc}"
                )

                final = {

                    "final_score": 0,

                    "should_signal": False,

                    "status": "REJECT",

                    "signal": "⛔ NO SIGNAL",

                    "reasons": [
                        "FINAL SIGNAL ENGINE ERROR"
                    ],
                }

            token["final_score"] = final.get(
                "final_score",
                0,
            )

            token["final_should_signal"] = final.get(
                "should_signal",
                False,
            )

            token["final_status"] = final.get(
                "status",
                "REJECT",
            )

            token["final_signal"] = final.get(
                "signal",
                "⛔ NO SIGNAL",
            )

            token["final_reasons"] = final.get(
                "reasons",
                [],
            )

            # =================================================
            # RECOMMENDATION
            # =================================================

            try:

                recommendation = (
                    RecommendationEngine.recommend(
                        token
                    )
                )

            except Exception as exc:

                print(
                    f"Recommendation error "
                    f"for {address}: {exc}"
                )

                recommendation = {

                    "recommendation_score": 0,

                    "recommendation":
                        "⏳ WAIT FOR DATA",

                    "action": "WAIT",

                    "confidence": 0,

                    "risk_level":
                        "⚪ UNKNOWN",

                    "market_stage":
                        "UNKNOWN",

                    "hard_reject": True,

                    "security_pass": False,

                    "final_should_signal": False,

                    "positive_reasons": [],

                    "risk_flags": [
                        "RECOMMENDATION ENGINE ERROR"
                    ],

                    "summary":
                        "Recommendation engine error",

                    "is_recommended": False,
                }

            # =================================================
            # SAVE RECOMMENDATION
            # =================================================

            token["recommendation_score"] = (
                recommendation.get(
                    "recommendation_score",
                    0,
                )
            )

            token["recommendation"] = (
                recommendation.get(
                    "recommendation",
                    "⏳ WAIT FOR DATA",
                )
            )

            token["recommendation_action"] = (
                recommendation.get(
                    "action",
                    "WAIT",
                )
            )

            token["recommendation_confidence"] = (
                recommendation.get(
                    "confidence",
                    0,
                )
            )

            token["recommendation_risk"] = (
                recommendation.get(
                    "risk_level",
                    "⚪ UNKNOWN",
                )
            )

            token["recommendation_market_stage"] = (
                recommendation.get(
                    "market_stage",
                    "UNKNOWN",
                )
            )

            token["recommendation_hard_reject"] = (
                recommendation.get(
                    "hard_reject",
                    False,
                )
            )

            token["recommendation_positive_reasons"] = (
                recommendation.get(
                    "positive_reasons",
                    [],
                )
            )

            token["recommendation_risk_flags"] = (
                recommendation.get(
                    "risk_flags",
                    [],
                )
            )

            token["recommendation_summary"] = (
                recommendation.get(
                    "summary",
                    "",
                )
            )

            token["is_recommended"] = (
                recommendation.get(
                    "is_recommended",
                    False,
                )
            )

            # =================================================
            # V7 SIGNAL CATEGORY
            # =================================================

            token["signal_priority"] = (
                self.SIGNAL_PRIORITY.get(
                    token.get(
                        "final_signal",
                        "⛔ NO SIGNAL",
                    ),
                    0,
                )
            )

            token["status_priority"] = (
                self.STATUS_PRIORITY.get(
                    token.get(
                        "final_status",
                        "REJECT",
                    ),
                    0,
                )
            )

            # =================================================
            # ADD
            # =================================================

            results.append(
                token
            )

        # =====================================================
        # V7 SMART RANKING
        # =====================================================

        results.sort(
            key=self._ranking_key,
            reverse=True,
        )

        # =====================================================
        # RANK
        # =====================================================

        for index, token in enumerate(
            results,
            start=1,
        ):

            token["rank"] = index

        # =====================================================
        # SIGNAL GROUP COUNTS
        # =====================================================

        strong_count = sum(
            1
            for token in results
            if token.get("final_signal")
            == "🔥 STRONG GEM"
        )

        gem_count = sum(
            1
            for token in results
            if token.get("final_signal")
            == "🚀 GEM SIGNAL"
        )

        early_count = sum(
            1
            for token in results
            if token.get("final_signal")
            == "👀 EARLY GEM"
        )

        watch_count = sum(
            1
            for token in results
            if token.get("final_signal")
            == "🟡 WATCH"
        )

        reject_count = sum(
            1
            for token in results
            if token.get("final_signal")
            == "⛔ NO SIGNAL"
        )

        # =====================================================
        # DEBUG
        # =====================================================

        print(
            f"🏆 Ranked candidates: "
            f"{len(results)}"
        )

        print(
            "📊 V7 SIGNAL GROUPS: "
            f"🔥 {strong_count} | "
            f"🚀 {gem_count} | "
            f"👀 {early_count} | "
            f"🟡 {watch_count} | "
            f"⛔ {reject_count}"
        )

        for token in results[:10]:

            print(
                f"🏆 #{token.get('rank')} "
                f"${token.get('symbol')} "
                f"{token.get('final_signal')} "
                f"REC={token.get('recommendation_score')} "
                f"FINAL={token.get('final_score')} "
                f"GEM={token.get('gem_score')} "
                f"AI={token.get('ai_score')} "
                f"SEC={token.get('security_score')}"
            )

        return results

    # =========================================================
    # V7 RANKING KEY
    # =========================================================

    @classmethod
    def _ranking_key(
        cls,
        token: Dict[str, Any],
    ):

        signal = token.get(
            "final_signal",
            "⛔ NO SIGNAL",
        )

        status = token.get(
            "final_status",
            "REJECT",
        )

        final_should_signal = bool(
            token.get(
                "final_should_signal",
                False,
            )
        )

        is_recommended = bool(
            token.get(
                "is_recommended",
                False,
            )
        )

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

        volume_24h = cls._number(
            token.get(
                "volume24h",
                0,
            )
        )

        buy_ratio = cls._number(
            token.get(
                "buy_ratio",
                0,
            )
        )

        # =====================================================
        # SIGNAL CATEGORY FIRST
        # =====================================================

        return (

            cls.SIGNAL_PRIORITY.get(
                signal,
                0,
            ),

            cls.STATUS_PRIORITY.get(
                status,
                0,
            ),

            final_should_signal,

            is_recommended,

            recommendation_score,

            final_score,

            gem_score,

            ai_score,

            security_score,

            buy_ratio,

            volume_24h,
        )

    # =========================================================
    # NUMBER
    # =========================================================

    @staticmethod
    def _number(
        value: Any,
    ) -> float:

        try:

            if value is None:

                return 0.0

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0
