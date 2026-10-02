import re
import time
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
        "robinhood": "🟢 Robinhood Chain",
        "arc": "🟠 Arc",
    }

    # =========================================================
    # SMALL-CAP GEM FILTERS
    # =========================================================

    MIN_MARKETCAP = 10_000
    MAX_MARKETCAP = 1_000_000

    # Pair-age window for discovery/signals.
    # Minimum age is 1 second; maximum age is 48 hours.
    # Missing/invalid pair age is rejected because the bot cannot safely
    # verify when the pair was created.
    MIN_TOKEN_AGE_SECONDS = 1
    EVM_MIN_TOKEN_AGE_SECONDS = 1
    MAX_TOKEN_AGE_SECONDS = 48 * 60 * 60

    SOLANA_MIN_MARKETCAP = 10_000
    SOLANA_MAX_MARKETCAP = 1_000_000
    SOLANA_MIN_LIQUIDITY = 10_000
    SOLANA_MAX_LIQUIDITY = 200_000
    SOLANA_MIN_VOLUME_6H = 2_000
    SOLANA_MIN_TXNS_1H = 10

    # Base / EVM discovery filters.
    # Security hard-blocks remain downstream and are NOT weakened.
    BASE_MIN_MARKETCAP = 10_000
    BASE_MAX_MARKETCAP = 1_000_000
    BASE_MIN_LIQUIDITY = 3_000
    BASE_MAX_LIQUIDITY = 150_000
    BASE_MIN_VOLUME_6H = 2_000
    BASE_MIN_TXNS_1H = 10

    ROBINHOOD_MIN_MARKETCAP = 10_000
    ROBINHOOD_MAX_MARKETCAP = 1_000_000
    ROBINHOOD_MIN_LIQUIDITY = 3_000
    ROBINHOOD_MAX_LIQUIDITY = 150_000
    ROBINHOOD_MIN_VOLUME_6H = 2_000
    ROBINHOOD_MIN_TXNS_1H = 10

    ARC_MIN_MARKETCAP = 10_000
    ARC_MAX_MARKETCAP = 1_000_000
    ARC_MIN_LIQUIDITY = 3_000
    ARC_MAX_LIQUIDITY = 150_000
    ARC_MIN_VOLUME_6H = 2_000
    ARC_MIN_TXNS_1H = 10

    MIN_BUY_RATIO = 0.45

    # =========================================================
    # ADDRESS DETECTION
    # =========================================================

    EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

    @classmethod
    def _looks_like_contract_address(cls, value: Any) -> bool:
        """Return True when a query looks like a real token address."""

        text = str(value or "").strip()

        if cls.EVM_ADDRESS_RE.fullmatch(text):
            return True

        # Solana base58 public keys are normally 32-44 characters.
        if 32 <= len(text) <= 44 and re.fullmatch(
            r"[1-9A-HJ-NP-Za-km-z]+",
            text,
        ):
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
        "base chain",
        "base meme",
        "base ai",
        "new base",
        "base launch",
        "base launchpad",
        "base fairlaunch",
        "base community",
        "base degen",
        "base pump",
        "base viral",
        "base dog",
        "base cat",
        "base inu",
        "base pepe",
        "base moon",
        "base token",
        "base gem",
        "base microcap",
        "base smallcap",
        "base eth",
        "meme",
        "ai",
        "dog",
        "cat",
        "inu",
        "pepe",
        "moon",
        "degen",
        "pump",
        "viral",
        "aerodrome",
        "brett",
        "toshi",
        "virtual",
        "clanker",
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
        self.gem_intelligence = GemIntelligence(
            confirmation_scans=3
        )

        self.last_scan_stats = {
            "chain": "",
            "raw_pairs": 0,
            "unique_tokens": 0,
            "marketcap_rejected": 0,
            "liquidity_rejected": 0,
            "volume_rejected": 0,
            "txns_rejected": 0,
            "buy_ratio_rejected": 0,
            "age_rejected": 0,
            "scored": 0,
            "returned": 0,
        }

    # =========================================================
    # CHAIN QUALITY CONFIG
    # =========================================================

    @classmethod
    def _chain_quality_config(
        cls,
        chain: str,
    ) -> Tuple[float, float, float, float, float]:
        """
        Return:

        min_marketcap
        max_marketcap
        min_liquidity
        max_liquidity
        min_volume_6h
        min_txns_1h

        This helper keeps pool selection and final processing using
        exactly the same hard market filters.
        """

        if chain == "solana":
            return (
                cls.SOLANA_MIN_MARKETCAP,
                cls.SOLANA_MAX_MARKETCAP,
                cls.SOLANA_MIN_LIQUIDITY,
                cls.SOLANA_MAX_LIQUIDITY,
                cls.SOLANA_MIN_VOLUME_6H,
                cls.SOLANA_MIN_TXNS_1H,
            )

        if chain == "robinhood":
            return (
                cls.ROBINHOOD_MIN_MARKETCAP,
                cls.ROBINHOOD_MAX_MARKETCAP,
                cls.ROBINHOOD_MIN_LIQUIDITY,
                cls.ROBINHOOD_MAX_LIQUIDITY,
                cls.ROBINHOOD_MIN_VOLUME_6H,
                cls.ROBINHOOD_MIN_TXNS_1H,
            )

        if chain == "arc":
            return (
                cls.ARC_MIN_MARKETCAP,
                cls.ARC_MAX_MARKETCAP,
                cls.ARC_MIN_LIQUIDITY,
                cls.ARC_MAX_LIQUIDITY,
                cls.ARC_MIN_VOLUME_6H,
                cls.ARC_MIN_TXNS_1H,
            )

        return (
            cls.BASE_MIN_MARKETCAP,
            cls.BASE_MAX_MARKETCAP,
            cls.BASE_MIN_LIQUIDITY,
            cls.BASE_MAX_LIQUIDITY,
            cls.BASE_MIN_VOLUME_6H,
            cls.BASE_MIN_TXNS_1H,
        )

    # =========================================================
    # PAIR AGE
    # =========================================================

    @classmethod
    def _pair_age(
        cls,
        pair: Dict[str, Any],
        chain: str,
    ) -> Tuple[float, float, bool]:
        """
        Return:

        created_seconds
        age_seconds
        age_valid

        Invalid/missing pairCreatedAt is never treated as fresh.
        """

        created_seconds = 0.0

        try:
            raw_created = pair.get(
                "pairCreatedAt"
            )

            created_value = float(
                raw_created or 0
            )

            # DexScreener normally supplies milliseconds.
            if created_value > 10_000_000_000:
                created_seconds = created_value / 1000.0
            else:
                created_seconds = created_value

            age_seconds = (
                time.time() - created_seconds
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            created_seconds = 0.0
            age_seconds = float("inf")

        min_age = (
            cls.EVM_MIN_TOKEN_AGE_SECONDS
            if chain in (
                "base",
                "robinhood",
                "arc",
            )
            else cls.MIN_TOKEN_AGE_SECONDS
        )

        age_valid = (
            created_seconds > 0
            and age_seconds >= min_age
            and age_seconds <= cls.MAX_TOKEN_AGE_SECONDS
        )

        return (
            created_seconds,
            age_seconds,
            age_valid,
        )

    # =========================================================
    # PAIR MARKET SNAPSHOT
    # =========================================================

    @classmethod
    def _pair_market_snapshot(
        cls,
        pair: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Extract all market values needed for pool selection.

        The scanner uses this during pool selection so that a fresh
        Base pool with good market data is not hidden by another pool
        belonging to the same token.
        """

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

        h1 = txns.get(
            "h1"
        ) or {}

        marketcap = cls._number(
            pair.get("marketCap")
            or pair.get("fdv")
            or 0
        )

        liquidity_usd = cls._number(
            liquidity.get("usd")
            or 0
        )

        volume_6h = cls._number(
            volume.get("h6")
            or volume.get("h24")
            or 0
        )

        buys_24h = cls._number(
            h24.get("buys")
            or 0
        )

        sells_24h = cls._number(
            h24.get("sells")
            or 0
        )

        total_24h = (
            buys_24h + sells_24h
        )

        buy_ratio = (
            buys_24h / total_24h
            if total_24h > 0
            else 0.0
        )

        buys_1h = cls._number(
            h1.get("buys")
            or 0
        )

        sells_1h = cls._number(
            h1.get("sells")
            or 0
        )

        txns_1h = (
            buys_1h + sells_1h
        )

        return {
            "marketcap": marketcap,
            "liquidity": liquidity_usd,
            "volume_6h": volume_6h,
            "txns_1h": txns_1h,
            "buy_ratio": buy_ratio,
            "buys_24h": buys_24h,
            "sells_24h": sells_24h,
        }

    # =========================================================
    # PAIR QUALITY
    # =========================================================

    @classmethod
    def _pair_quality(
        cls,
        pair: Dict[str, Any],
        chain: str,
    ) -> Dict[str, Any]:
        """
        Determine whether a pool satisfies the scanner's hard
        market filters.

        IMPORTANT:
        This does NOT bypass any filter.

        It is only used to choose the strongest valid-age pool
        when DexScreener returns multiple pools for one token.
        """

        snapshot = cls._pair_market_snapshot(
            pair
        )

        (
            min_mc,
            max_mc,
            min_liq,
            max_liq,
            min_vol_6h,
            min_txns_1h,
        ) = cls._chain_quality_config(
            chain
        )

        marketcap_ok = (
            min_mc
            <= snapshot["marketcap"]
            <= max_mc
        )

        liquidity_ok = (
            min_liq
            <= snapshot["liquidity"]
            <= max_liq
        )

        volume_ok = (
            snapshot["volume_6h"]
            >= min_vol_6h
        )

        txns_ok = (
            snapshot["txns_1h"]
            >= min_txns_1h
        )

        buy_ratio_ok = (
            snapshot["buy_ratio"]
            >= cls.MIN_BUY_RATIO
        )

        hard_quality_pass = (
            marketcap_ok
            and liquidity_ok
            and volume_ok
            and txns_ok
            and buy_ratio_ok
        )

        quality_count = sum(
            [
                marketcap_ok,
                liquidity_ok,
                volume_ok,
                txns_ok,
                buy_ratio_ok,
            ]
        )

        return {
            "hard_quality_pass": hard_quality_pass,
            "quality_count": quality_count,
            **snapshot,
        }

    # =========================================================
    # POOL SELECTION
    # =========================================================

    @classmethod
    def _select_best_pools(
        cls,
        pairs: List[Dict[str, Any]],
        chain: str,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Select one useful pool per token.

        OLD PROBLEM:
        The scanner selected the strongest pool mainly by liquidity.
        A token could have:

            Pool A = old + high liquidity
            Pool B = fresh + valid liquidity

        and pool selection could hide Pool B.

        NEW BEHAVIOUR:
        1. Group all pools by token.
        2. Prefer fresh 1s-48h pools.
        3. Among fresh pools, prefer pools that actually satisfy
           the hard market filters.
        4. Among equal-quality pools, prefer liquidity/volume/txns.
        5. If no fresh pool exists, retain the strongest old/missing-age
           pool only for diagnostics, where the normal age filter will
           reject it later.

        No safety gate is weakened.
        """

        grouped: Dict[
            str,
            List[Dict[str, Any]]
        ] = {}

        for pair in pairs:

            if not isinstance(
                pair,
                dict,
            ):
                continue

            pair_chain = str(
                pair.get(
                    "chainId",
                    "",
                )
                or ""
            ).lower().strip()

            if pair_chain != chain:
                continue

            base = pair.get(
                "baseToken"
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

            grouped.setdefault(
                address.lower(),
                []
            ).append(
                pair
            )

        selected = []
        age_rejected_candidates = 0

        for address, token_pairs in grouped.items():

            fresh_candidates = []
            old_candidates = []

            for pair in token_pairs:

                _, _, age_valid = cls._pair_age(
                    pair,
                    chain,
                )

                quality = cls._pair_quality(
                    pair,
                    chain,
                )

                if age_valid:

                    # HARD QUALITY PASS gets priority.
                    #
                    # This is important for Base because a token
                    # can have several fresh pools with very different
                    # liquidity/volume/transaction data.
                    candidate_key = (
                        1 if quality["hard_quality_pass"] else 0,
                        quality["quality_count"],
                        quality["liquidity"],
                        quality["volume_6h"],
                        quality["txns_1h"],
                        quality["buy_ratio"],
                    )

                    fresh_candidates.append(
                        (
                            candidate_key,
                            pair,
                        )
                    )

                else:

                    # Old/missing-age pools are kept only as a fallback
                    # for diagnostics. The processing stage will reject
                    # them by the normal age gate.
                    old_key = (
                        quality["hard_quality_pass"],
                        quality["quality_count"],
                        quality["liquidity"],
                        quality["volume_6h"],
                        quality["txns_1h"],
                        quality["buy_ratio"],
                    )

                    old_candidates.append(
                        (
                            old_key,
                            pair,
                        )
                    )

            if fresh_candidates:

                fresh_candidates.sort(
                    key=lambda item: item[0],
                    reverse=True,
                )

                selected.append(
                    fresh_candidates[0][1]
                )

            elif old_candidates:

                old_candidates.sort(
                    key=lambda item: item[0],
                    reverse=True,
                )

                selected.append(
                    old_candidates[0][1]
                )

                age_rejected_candidates += 1

        return (
            selected,
            age_rejected_candidates,
        )

    # =========================================================
    # SCAN
    # =========================================================

    async def scan(
        self,
        query="sol",
    ):

        if not hasattr(
            self,
            "gem_intelligence",
        ):
            self.gem_intelligence = GemIntelligence(
                confirmation_scans=3
            )

        # -----------------------------------------------------
        # DETECT CHAIN
        # -----------------------------------------------------

        requested_chain = "solana"

        self.last_scan_stats = {
            "chain": requested_chain,
            "raw_pairs": 0,
            "unique_tokens": 0,
            "marketcap_rejected": 0,
            "liquidity_rejected": 0,
            "volume_rejected": 0,
            "txns_rejected": 0,
            "buy_ratio_rejected": 0,
            "age_rejected": 0,
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
                "robinhood",
                "robinhood chain",
                "rh",
                "hood",
            ):

                requested_chain = "robinhood"
                query = None

            elif raw_query in (
                "arc",
                "arc network",
                "arc chain",
            ):

                requested_chain = "arc"
                query = None

            elif raw_query in (
                "sol",
                "solana",
                "solana network",
            ):

                requested_chain = "solana"
                query = None

        self.last_scan_stats[
            "chain"
        ] = requested_chain

        # -----------------------------------------------------
        # EXACT ADDRESS LOOKUP
        # -----------------------------------------------------

        if query:
            query = str(
                query
            ).strip()

        if (
            query
            and self._looks_like_contract_address(
                query
            )
        ):

            print(
                f"🎯 Exact address lookup: {query}"
            )

            try:

                pairs = await self.dex.tokens(
                    [query]
                )

            except Exception as exc:

                print(
                    f"❌ Exact address lookup failed: {exc}"
                )

                return []

            pairs = [
                pair
                for pair in pairs
                if (
                    isinstance(pair, dict)
                    and str(
                        pair.get(
                            "chainId",
                            "",
                        )
                    ).lower().strip()
                    == requested_chain
                    and str(
                        (
                            pair.get(
                                "baseToken"
                            )
                            or {}
                        ).get(
                            "address",
                            "",
                        )
                    ).strip().lower()
                    == query.lower()
                )
            ]

            if not pairs:

                print(
                    f"❌ Address not found on "
                    f"{requested_chain}: {query}"
                )

                return []

        else:

            # -----------------------------------------------------
            # DISCOVERY QUERIES
            # -----------------------------------------------------

            if requested_chain in (
                "base",
                "robinhood",
                "arc",
            ):

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
                    query.lower()
                    not in [
                        str(item).lower()
                        for item in queries
                    ]
                ):

                    queries.insert(
                        0,
                        query,
                    )

            # -----------------------------------------------------
            # DISCOVERY
            # -----------------------------------------------------

            try:

                if requested_chain == "solana":

                    pairs = await self.dex.discover_solana(
                        queries
                    )

                else:

                    pairs = await self.dex.discover_chain(
                        requested_chain,
                        queries,
                    )

            except Exception as exc:

                print(
                    f"❌ "
                    f"{self.SUPPORTED_CHAINS.get(
                        requested_chain,
                        requested_chain,
                    )} "
                    f"discovery failed: {exc}"
                )

                return []

        self.last_scan_stats[
            "raw_pairs"
        ] = len(pairs)

        print(
            f"📊 Raw "
            f"{self.SUPPORTED_CHAINS.get(
                requested_chain,
                requested_chain,
            )} candidates: "
            f"{len(pairs)}"
        )

        results = []

        # =====================================================
        # MULTI-POOL SELECTION
        # =====================================================

        selected_pairs, fallback_age_rejected = (
            self._select_best_pools(
                pairs,
                requested_chain,
            )
        )

        self.last_scan_stats[
            "unique_tokens"
        ] = len(selected_pairs)

        print(
            f"📌 {requested_chain.upper()} unique tokens "
            f"after multi-pool selection: "
            f"{len(selected_pairs)}"
        )

        if fallback_age_rejected:
            print(
                f"⏱️ {requested_chain.upper()} tokens with "
                f"no valid 1s-48h pool: "
                f"{fallback_age_rejected}"
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
                or ""
            ).lower().strip()

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
            # HARD TOKEN AGE FILTER
            # =================================================

            pair_created = pair.get(
                "pairCreatedAt"
            )

            # IMPORTANT:
            # Initialize this BEFORE try so malformed/missing
            # pairCreatedAt can never create an undefined variable.
            created_seconds = 0.0

            try:

                created_value = float(
                    pair_created or 0
                )

                if created_value > 10_000_000_000:
                    created_seconds = (
                        created_value / 1000.0
                    )
                else:
                    created_seconds = created_value

                token_age_seconds = (
                    time.time()
                    - created_seconds
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):

                created_seconds = 0.0
                token_age_seconds = float(
                    "inf"
                )

            min_age_seconds = (
                self.EVM_MIN_TOKEN_AGE_SECONDS
                if requested_chain in (
                    "base",
                    "robinhood",
                    "arc",
                )
                else self.MIN_TOKEN_AGE_SECONDS
            )

            if (
                created_seconds <= 0
                or token_age_seconds < 0
                or token_age_seconds < min_age_seconds
                or token_age_seconds > self.MAX_TOKEN_AGE_SECONDS
            ):

                self.last_scan_stats[
                    "age_rejected"
                ] += 1

                continue

            # =================================================
            # CHAIN-SPECIFIC QUALITY FILTER
            # =================================================

            (
                min_mc,
                max_mc,
                min_liq,
                max_liq,
                min_vol_6h,
                min_txns_1h,
            ) = self._chain_quality_config(
                requested_chain
            )

            volume_6h = self._number(
                volume.get(
                    "h6"
                )
                or 0
            )

            h1 = txns.get(
                "h1"
            ) or {}

            txns_1h = (
                self._number(
                    h1.get(
                        "buys"
                    )
                    or 0
                )
                + self._number(
                    h1.get(
                        "sells"
                    )
                    or 0
                )
            )

            # -------------------------------------------------
            # MARKET CAP
            # -------------------------------------------------

            if (
                marketcap < min_mc
                or marketcap > max_mc
            ):

                self.last_scan_stats[
                    "marketcap_rejected"
                ] += 1

                continue

            # -------------------------------------------------
            # LIQUIDITY
            # -------------------------------------------------

            if (
                liquidity_usd < min_liq
                or liquidity_usd > max_liq
            ):

                self.last_scan_stats[
                    "liquidity_rejected"
                ] += 1

                continue

            # -------------------------------------------------
            # VOLUME
            # -------------------------------------------------

            if volume_6h < min_vol_6h:

                self.last_scan_stats[
                    "volume_rejected"
                ] += 1

                continue

            # -------------------------------------------------
            # TRANSACTIONS
            # -------------------------------------------------

            if txns_1h < min_txns_1h:

                self.last_scan_stats[
                    "txns_rejected"
                ] += 1

                continue

            # -------------------------------------------------
            # BUY RATIO
            # -------------------------------------------------

            if buy_ratio < self.MIN_BUY_RATIO:

                self.last_scan_stats[
                    "buy_ratio_rejected"
                ] += 1

                continue

            # =================================================
            # DEXSCREENER INFO
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

                "volume6h":
                    self._number(
                        volume.get(
                            "h6"
                        )
                        or 0
                    ),

                "txns1h": int(
                    txns_1h
                ),

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

                "pair_age_seconds":
                    token_age_seconds,

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

                "price_change_5m":
                    self._number(
                        price_change.get(
                            "m5"
                        )
                        or 0
                    ),

                "price_change_15m":
                    self._number(
                        price_change.get(
                            "m15"
                        )
                        or 0
                    ),

                "price_change_1h":
                    self._number(
                        price_change.get(
                            "h1"
                        )
                        or 0
                    ),

                "volume_5m":
                    self._number(
                        volume.get(
                            "m5"
                        )
                        or 0
                    ),

                "volume_1h":
                    self._number(
                        volume.get(
                            "h1"
                        )
                        or 0
                    ),

                "buys5m": int(
                    self._number(
                        (
                            txns.get(
                                "m5"
                            )
                            or {}
                        ).get(
                            "buys"
                        )
                        or 0
                    )
                ),

                "sells5m": int(
                    self._number(
                        (
                            txns.get(
                                "m5"
                            )
                            or {}
                        ).get(
                            "sells"
                        )
                        or 0
                    )
                ),

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

            self.last_scan_stats[
                "scored"
            ] += 1

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

            token["ai_signal"] = ai.get(
                "signal",
                "🟡 NEUTRAL",
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
                    "total_txns": int(
                        total_txns
                    ),
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
                int(
                    total_txns
                ),
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
            # BASE / EVM SECURITY ENRICHMENT
            # =================================================

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
            # GEM INTELLIGENCE
            # =================================================

            try:

                intelligence = (
                    self.gem_intelligence.analyze(
                        token
                    )
                )

            except Exception as exc:

                print(
                    f"Gem intelligence error "
                    f"for {address}: {exc}"
                )

                intelligence = {
                    "gem_score_2": 0,
                    "confirmed_gem": False,
                    "signal_stage": "ERROR",
                }

            token.update(
                intelligence
            )

            if "gem_score_2" in intelligence:

                token["gem_score_legacy"] = (
                    token.get(
                        "gem_score",
                        0,
                    )
                )

                token["gem_score"] = (
                    intelligence[
                        "gem_score_2"
                    ]
                )

            # =================================================
            # DATA / SECURITY CONFIDENCE
            # =================================================

            required_market_fields = (
                marketcap > 0
                and liquidity_usd > 0
                and volume_24h > 0
                and total_txns > 0
            )

            security_evidence = 0

            if token.get(
                "security_should_pass"
            ):
                security_evidence += 1

            if (
                chain == "base"
                and token.get(
                    "honeypot_available"
                )
            ):
                security_evidence += 2

            elif (
                chain in (
                    "robinhood",
                    "arc",
                )
                and token.get(
                    "security_should_pass"
                )
            ):
                security_evidence += 1

            if chain == "solana":

                if token.get(
                    "mint_authority"
                ) is not None:
                    security_evidence += 1

                if token.get(
                    "freeze_authority"
                ) is not None:
                    security_evidence += 1

            if security_evidence >= 3:

                security_confidence = "HIGH"

            elif security_evidence >= 1:

                security_confidence = "MEDIUM"

            else:

                security_confidence = "LOW"

            token["market_data_complete"] = (
                required_market_fields
            )

            token["security_evidence_score"] = (
                security_evidence
            )

            token["security_confidence"] = (
                security_confidence
            )

            # =================================================
            # FINAL SIGNAL
            # =================================================

            try:

                final = (
                    FinalSignalEngine.evaluate(
                        token,
                        security,
                    )
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
                "final_signal",
                final.get(
                    "signal",
                    "⛔ NO SIGNAL",
                ),
            )

            # =================================================
            # CANONICAL SIGNAL
            # =================================================

            token["signal"] = (
                token["final_signal"]
            )

            token["signal_source"] = (
                "final_signal_engine"
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

            self.last_scan_stats[
                "returned"
            ] = len(results)

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
            "🧭 V10 PIPELINE: "
            f"raw={self.last_scan_stats['raw_pairs']} | "
            f"unique={self.last_scan_stats['unique_tokens']} | "
            f"scored={self.last_scan_stats['scored']} | "
            f"returned={self.last_scan_stats['returned']} | "
            f"MC_REJ={self.last_scan_stats['marketcap_rejected']} | "
            f"LIQ_REJ={self.last_scan_stats['liquidity_rejected']} | "
            f"VOL_REJ={self.last_scan_stats['volume_rejected']} | "
            f"TXN_REJ={self.last_scan_stats['txns_rejected']} | "
            f"BUY_REJ={self.last_scan_stats['buy_ratio_rejected']} | "
            f"AGE_REJ={self.last_scan_stats['age_rejected']}"
        )

        print(
            "📊 V10 SIGNAL GROUPS: "
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

        v9_gem = cls._number(
            token.get(
                "gem_score_2",
                gem_score,
            )
        )

        momentum = cls._number(
            token.get(
                "momentum_score",
                0,
            )
        )

        early = cls._number(
            token.get(
                "early_entry_score",
                0,
            )
        )

        confirmation = cls._number(
            token.get(
                "confirmation_count",
                0,
            )
        )

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
