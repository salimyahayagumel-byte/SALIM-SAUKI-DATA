import re
from typing import Any, Dict, List, Tuple

from services.dexscreener import DexScreener
from services.security import SecurityChecker
from services.final_signal import FinalSignalEngine

from ai.scoring import AIScoring
from ai.gem_detector import GemDetector
from ai.recommendation import RecommendationEngine
from services.gem_intelligence import GemIntelligence


class TokenScanner:

    # =========================================================
    # SUPPORTED CHAINS
    # =========================================================

    SUPPORTED_CHAINS = {
        "solana": "🟣 Solana",
        "base": "🔵 Base",
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
    # ADDRESS DETECTION
    # =========================================================

    EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

    @classmethod
    def _looks_like_contract_address(cls, value: Any) -> bool:
        """Return True when a query looks like a real token address.

        This prevents `/analyze <contract>` from being treated as a text
        search. Exact addresses should be resolved through DexScreener's
        token endpoint first, then pass through the normal scoring pipeline.
        """
        text = str(value or "").strip()
        if cls.EVM_ADDRESS_RE.fullmatch(text):
            return True

        # Solana base58 public keys are normally 32-44 characters and do
        # not contain the ambiguous base58 characters 0, O, I or l.
        if 32 <= len(text) <= 44 and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", text):
            return True

        return False

    # =========================================================
    # DISCOVERY QUERIES
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
    # BASE DISCOVERY QUERIES
    # =========================================================

    BASE_DISCOVERY_QUERIES = [
        "base",
        "meme",
        "ai",
        "dog",
        "cat",
        "inu",
        "pepe",
        "moon",
        "degen",
        "aerodrome",
    ]

    # =========================================================
    # SIGNAL PRIORITY
    # =========================================================

    SIGNAL_PRIORITY = {
        "🔥 STRONG GEM": 5,
        "🚀 GEM SIGNAL": 4,
        "👀 EARLY GEM": 3,
        "🟡 WATCH": 2,
        "⛔ NO SIGNAL": 0,
    }

    # =========================================================
    # STATUS PRIORITY
    # =========================================================

    STATUS_PRIORITY = {
        "STRONG GEM": 5,
        "GEM SIGNAL": 4,
        "EARLY GEM": 3,
        "WATCH": 2,
        "REJECT": 0,
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):

        self.dex = DexScreener()

        self.security = SecurityChecker()

        self.gem_detector = GemDetector()
        self.gem_intelligence = GemIntelligence(confirmation_scans=3)

        # V8.7 scan diagnostics. These counters explain exactly
        # where candidates disappear during automatic scanning.
        self.last_scan_stats = {
            "chain": "",
            "raw_pairs": 0,
            "unique_tokens": 0,
            "marketcap_rejected": 0,
            "liquidity_rejected": 0,
            "volume_rejected": 0,
            "txns_rejected": 0,
            "buy_ratio_rejected": 0,
            "scored": 0,
            "returned": 0,
        }

    # =========================================================
    # SCAN
    # =========================================================

    async def scan(
        self,
        query="sol",
    ):
        if not hasattr(self, "gem_intelligence"):
            self.gem_intelligence = GemIntelligence(confirmation_scans=3)

        # -----------------------------------------------------
        # DETECT CHAIN
        # -----------------------------------------------------

        requested_chain = "solana"

        # Reset per-scan diagnostics.
        self.last_scan_stats = {
            "chain": requested_chain,
            "raw_pairs": 0,
            "unique_tokens": 0,
            "marketcap_rejected": 0,
            "liquidity_rejected": 0,
            "volume_rejected": 0,
            "txns_rejected": 0,
            "buy_ratio_rejected": 0,
            "scored": 0,
            "returned": 0,
        }

        if query:

            raw_query = str(
                query
            ).strip().lower()

            if raw_query in (
                "base",
                "base network",
            ):

                requested_chain = "base"

                query = None

            elif raw_query in (
                "sol",
                "solana",
                "solana network",
            ):

                requested_chain = "solana"

                query = None

        self.last_scan_stats["chain"] = requested_chain

        # -----------------------------------------------------
        # EXACT ADDRESS LOOKUP
        # -----------------------------------------------------

        if query:

            query = str(query).strip()

        if query and self._looks_like_contract_address(query):

            print(
                f"🎯 Exact address lookup: {query}"
            )

            try:
                pairs = await self.dex.tokens([query])
            except Exception as exc:
                print(
                    f"❌ Exact address lookup failed: {exc}"
                )
                return []

            pairs = [
                pair
                for pair in pairs
                if isinstance(pair, dict)
                and str(pair.get("chainId", "")).lower().strip() == requested_chain
                and str((pair.get("baseToken") or {}).get("address", "")).strip().lower() == query.lower()
            ]

            if not pairs:
                print(
                    f"❌ Address not found on {requested_chain}: {query}"
                )
                return []

        else:

            # -----------------------------------------------------
            # DISCOVERY QUERIES
            # -----------------------------------------------------

            if requested_chain == "base":

                queries = list(
                    self.BASE_DISCOVERY_QUERIES
                )

            else:

                queries = list(
                    self.DISCOVERY_QUERIES
                )

            # -----------------------------------------------------
            # CUSTOM SEARCH QUERY
            # -----------------------------------------------------

            if query:

                if (
                    query
                    and query.lower()
                    not in [str(item).lower() for item in queries]
                ):

                    queries.insert(
                        0,
                        query,
                    )

            # -----------------------------------------------------
            # DISCOVERY
            # -----------------------------------------------------

            try:

                if requested_chain == "base":

                    pairs = await self.dex.discover_base(
                        queries
                    )

                else:

                    pairs = await self.dex.discover_solana(
                        queries
                    )

            except Exception as exc:

                print(
                    f"❌ {self.SUPPORTED_CHAINS.get(requested_chain, requested_chain)} "
                    f"discovery failed: {exc}"
                )

                return []

        self.last_scan_stats["raw_pairs"] = len(pairs)

        print(
            f"📊 Raw "
            f"{self.SUPPORTED_CHAINS.get(requested_chain, requested_chain)} "
            f"candidates: "
            f"{len(pairs)}"
        )

        results = []

        # =====================================================
        # SELECT BEST POOL PER TOKEN
        #
        # DexScreener can return multiple pools for the same
        # token. Processing the first pool is dangerous because
        # that pool may have weaker liquidity/volume than another
        # pool for the same token. Pick the strongest available
        # market-data pair first, then run the expensive security
        # and scoring pipeline only once per token.
        # =====================================================

        best_pairs = {}

        for pair in pairs:

            if not isinstance(pair, dict):
                continue

            chain = str(
                pair.get('chainId', '') or ''
            ).lower().strip()

            if chain != requested_chain:
                continue

            base = pair.get('baseToken') or {}
            address = str(
                base.get('address', '') or ''
            ).strip()

            if not address:
                continue

            liquidity = pair.get('liquidity') or {}
            volume = pair.get('volume') or {}
            txns = pair.get('txns') or {}
            h24 = txns.get('h24') or {}

            liq = self._number(liquidity.get('usd') or 0)
            vol = self._number(volume.get('h24') or 0)
            buys = self._number(h24.get('buys') or 0)
            sells = self._number(h24.get('sells') or 0)
            tx_count = buys + sells

            candidate_key = (liq, vol, tx_count)
            current = best_pairs.get(address)

            if current is None or candidate_key > current[0]:
                best_pairs[address] = (candidate_key, pair)

        selected_pairs = [
            item[1]
            for item in best_pairs.values()
        ]

        self.last_scan_stats["unique_tokens"] = len(selected_pairs)

        print(
            f"📌 {requested_chain.upper()} unique tokens after pool selection: "
            f"{len(selected_pairs)}"
        )

        # =====================================================
        # PROCESS SELECTED PAIRS
        # =====================================================

        for pair in selected_pairs:

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

            if chain != requested_chain:

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

            # =================================================
            # TOKEN ADDRESS
            # =================================================

            address = str(
                base.get(
                    "address",
                    "",
                )
                or ""
            ).strip()

            if not address:

                continue

            # =================================================
            # MARKET DATA
            # =================================================

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

            if (
                marketcap
                < self.MIN_MARKETCAP
            ):

                self.last_scan_stats["marketcap_rejected"] += 1
                continue

            if (
                marketcap
                > self.MAX_MARKETCAP
            ):

                self.last_scan_stats["marketcap_rejected"] += 1
                continue

            if (
                liquidity_usd
                < self.MIN_LIQUIDITY
            ):

                self.last_scan_stats["liquidity_rejected"] += 1
                continue

            if (
                volume_24h
                < self.MIN_VOLUME_24H
            ):

                self.last_scan_stats["volume_rejected"] += 1
                continue

            if (
                total_txns
                < self.MIN_TXNS
            ):

                self.last_scan_stats["txns_rejected"] += 1
                continue

            if (
                buy_ratio
                < self.MIN_BUY_RATIO
            ):

                self.last_scan_stats["buy_ratio_rejected"] += 1
                continue

            # =================================================
            # DEXSCREENER INFO
            #
            # This contains:
            #
            # info.imageUrl
            # info.header
            # info.openGraph
            # info.websites
            # info.socials
            # =================================================

            info = pair.get(
                "info"
            ) or {}

            if not isinstance(
                info,
                dict,
            ):

                info = {}

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
                    self.SUPPORTED_CHAINS.get(
                        chain,
                        "🟣 Solana",
                    ),

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

                "price_change_5m": self._number(price_change.get("m5") or 0),
                "price_change_15m": self._number(price_change.get("m15") or 0),
                "price_change_1h": self._number(price_change.get("h1") or 0),
                "volume_5m": self._number(volume.get("m5") or 0),
                "volume_1h": self._number(volume.get("h1") or 0),
                "buys5m": int(self._number((txns.get("m5") or {}).get("buys") or 0)),
                "sells5m": int(self._number((txns.get("m5") or {}).get("sells") or 0)),

                "url": pair.get(
                    "url"
                ),

                # =================================================
                # SOCIAL / WEBSITE INFORMATION
                # =================================================

                "info": info,

                "websites":
                    info.get(
                        "websites",
                        [],
                    ) or [],

                "socials":
                    info.get(
                        "socials",
                        [],
                    ) or [],

                "image_url":
                    info.get(
                        "imageUrl"
                    ),

                "header_url":
                    info.get(
                        "header"
                    ),

                "open_graph_url":
                    info.get(
                        "openGraph"
                    ),

                "quote_token":
                    pair.get(
                        "quoteToken"
                    ) or {},
            }

            # =================================================
            # AI SCORING
            # =================================================

            self.last_scan_stats["scored"] += 1

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

            # Base/EVM security enrichment. These fields are harmless
            # on Solana and let the final signal/dashboard expose the
            # stronger Honeypot.is checks when the token is on Base.
            token["honeypot_available"] = security.get(
                "honeypot_available",
                False,
            )
            token["honeypot_risk"] = security.get(
                "honeypot_risk"
            )
            token["honeypot_risk_level"] = security.get(
                "honeypot_risk_level"
            )
            token["honeypot_detected"] = security.get(
                "honeypot_detected"
            )
            token["buy_tax"] = security.get(
                "buy_tax"
            )
            token["sell_tax"] = security.get(
                "sell_tax"
            )
            token["contract_open_source"] = security.get(
                "contract_open_source"
            )
            token["proxy_calls"] = security.get(
                "proxy_calls"
            )

            # =================================================
            # V9 GEM INTELLIGENCE
            # =================================================
            try:
                intelligence = self.gem_intelligence.analyze(token)
            except Exception as exc:
                print(f"Gem intelligence error for {address}: {exc}")
                intelligence = {
                    "gem_score_2": 0,
                    "confirmed_gem": False,
                    "signal_stage": "ERROR",
                }

            token.update(intelligence)

            if "gem_score_2" in intelligence:
                token["gem_score_legacy"] = token.get("gem_score", 0)
                token["gem_score"] = intelligence["gem_score_2"]

            # =================================================
            # DATA / SECURITY CONFIDENCE
            # =================================================
            # A high score must never be confused with complete evidence.
            # Keep a separate quality indicator so downstream UI/AI layers
            # can distinguish strong market data from incomplete data.
            required_market_fields = (
                marketcap > 0
                and liquidity_usd > 0
                and volume_24h > 0
                and total_txns > 0
            )

            security_evidence = 0

            if token.get("security_should_pass"):
                security_evidence += 1

            if chain == "base" and token.get("honeypot_available"):
                security_evidence += 2

            if chain == "solana":
                if token.get("mint_authority") is not None:
                    security_evidence += 1
                if token.get("freeze_authority") is not None:
                    security_evidence += 1

            if security_evidence >= 3:
                security_confidence = "HIGH"
            elif security_evidence >= 1:
                security_confidence = "MEDIUM"
            else:
                security_confidence = "LOW"

            token["market_data_complete"] = required_market_fields
            token["security_evidence_score"] = security_evidence
            token["security_confidence"] = security_confidence

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
            # SIGNAL CATEGORY
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
            # ADD RESULT
            # =================================================

            results.append(
                token
            )

            self.last_scan_stats["returned"] = len(results)

        # =====================================================
        # SMART RANKING
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
            if token.get(
                "final_signal"
            )
            == "🔥 STRONG GEM"
        )

        gem_count = sum(
            1
            for token in results
            if token.get(
                "final_signal"
            )
            == "🚀 GEM SIGNAL"
        )

        early_count = sum(
            1
            for token in results
            if token.get(
                "final_signal"
            )
            == "👀 EARLY GEM"
        )

        watch_count = sum(
            1
            for token in results
            if token.get(
                "final_signal"
            )
            == "🟡 WATCH"
        )

        reject_count = sum(
            1
            for token in results
            if token.get(
                "final_signal"
            )
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
            "🧭 V8.7 PIPELINE: "
            f"raw={self.last_scan_stats['raw_pairs']} | "
            f"unique={self.last_scan_stats['unique_tokens']} | "
            f"scored={self.last_scan_stats['scored']} | "
            f"returned={self.last_scan_stats['returned']} | "
            f"MC_REJ={self.last_scan_stats['marketcap_rejected']} | "
            f"LIQ_REJ={self.last_scan_stats['liquidity_rejected']} | "
            f"VOL_REJ={self.last_scan_stats['volume_rejected']} | "
            f"TXN_REJ={self.last_scan_stats['txns_rejected']} | "
            f"BUY_REJ={self.last_scan_stats['buy_ratio_rejected']}"
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
    # RANKING KEY
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

        signal_priority = cls._number(
            token.get(
                "signal_priority",
                0,
            )
        )

        status_priority = cls._number(
            token.get(
                "status_priority",
                0,
            )
        )

        v9_gem = cls._number(token.get("gem_score_2", gem_score))
        momentum = cls._number(token.get("momentum_score", 0))
        early = cls._number(token.get("early_entry_score", 0))
        confirmation = cls._number(token.get("confirmation_count", 0))

        return (
            signal_priority,
            status_priority,
            recommendation_score,
            final_score,
            v9_gem,
            confirmation,
            momentum,
            early,
            gem_score,
            ai_score,
            security_score,
            buy_ratio,
            liquidity_ratio,
            volume_ratio,
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
