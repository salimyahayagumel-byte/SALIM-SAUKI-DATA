import asyncio
from typing import Any, Dict, List, Optional

import httpx


SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"

TOKEN_PROFILES_URL = (
    "https://api.dexscreener.com/token-profiles/latest/v1"
)

BOOSTS_URL = (
    "https://api.dexscreener.com/token-boosts/latest/v1"
)

TOP_BOOSTS_URL = (
    "https://api.dexscreener.com/token-boosts/top/v1"
)

TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens"

# DexScreener search is useful for discovery, but it is not a dedicated
# "new Base pools" feed. GeckoTerminal provides a public new-pools feed;
# we use it only as an additional Base discovery source and then enrich
# the discovered token addresses through DexScreener so the existing
# scanner/security/filter pipeline remains authoritative.
GECKO_NEW_POOLS_URL = (
    "https://api.geckoterminal.com/api/v2/networks/{network}/new_pools"
)


class DexScreener:

    def __init__(self):

        self.timeout = httpx.Timeout(
            connect=15.0,
            read=30.0,
            write=15.0,
            pool=15.0,
        )

        self.headers = {
            "Accept": "application/json",
            "User-Agent": "SALIM-SAUKI-DATA/2.0",
        }

    # =========================================================
    # GENERIC GET
    # =========================================================

    async def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ):

        for attempt in range(1, retries + 1):

            try:

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=self.headers,
                    trust_env=False,
                    http2=False,
                ) as client:

                    response = await client.get(
                        url,
                        params=params,
                    )

                    response.raise_for_status()

                    return response.json()

            except httpx.TimeoutException as exc:

                print(
                    f"DexScreener timeout "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            except httpx.HTTPStatusError as exc:

                print(
                    f"DexScreener HTTP error "
                    f"(attempt {attempt}/{retries}): "
                    f"{exc.response.status_code} - "
                    f"{exc.response.url}"
                )

            except httpx.RequestError as exc:

                print(
                    f"DexScreener connection error "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            except Exception as exc:

                print(
                    f"DexScreener unexpected error "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            if attempt < retries:
                await asyncio.sleep(
                    min(2 * attempt, 6)
                )

        return None

    # =========================================================
    # SEARCH
    # =========================================================

    async def search(
        self,
        query: str,
        retries: int = 3,
    ) -> List[Dict[str, Any]]:

        query = str(query or "").strip()

        if not query:
            return []

        data = await self._get(
            SEARCH_URL,
            params={"q": query},
            retries=retries,
        )

        if not isinstance(data, dict):
            return []

        pairs = data.get("pairs", [])

        if not isinstance(pairs, list):
            return []

        return [
            item
            for item in pairs
            if isinstance(item, dict)
        ]

    # =========================================================
    # TOKEN PROFILES
    # =========================================================

    async def latest_token_profiles(
        self,
        retries: int = 3,
    ) -> List[Dict[str, Any]]:

        data = await self._get(
            TOKEN_PROFILES_URL,
            retries=retries,
        )

        if not isinstance(data, list):
            return []

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    # =========================================================
    # LATEST BOOSTS
    # =========================================================

    async def latest_boosts(
        self,
        retries: int = 3,
    ) -> List[Dict[str, Any]]:

        data = await self._get(
            BOOSTS_URL,
            retries=retries,
        )

        if not isinstance(data, list):
            return []

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    # =========================================================
    # TOP BOOSTS
    # =========================================================

    async def top_boosts(
        self,
        retries: int = 3,
    ) -> List[Dict[str, Any]]:

        data = await self._get(
            TOP_BOOSTS_URL,
            retries=retries,
        )

        if not isinstance(data, list):
            return []

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    # =========================================================
    # TOKEN PAIRS BY ADDRESSES
    # =========================================================

    async def tokens(
        self,
        addresses: List[str],
        retries: int = 3,
    ) -> List[Dict[str, Any]]:

        clean_addresses = []
        seen = set()

        for address in addresses:

            address = str(address or "").strip()

            if not address:
                continue

            address_key = address.lower()

            if address_key in seen:
                continue

            seen.add(address_key)
            clean_addresses.append(address)

        if not clean_addresses:
            return []

        joined = ",".join(clean_addresses)

        url = f"{TOKENS_URL}/{joined}"

        data = await self._get(
            url,
            retries=retries,
        )

        if not isinstance(data, dict):
            return []

        pairs = data.get("pairs", [])

        if not isinstance(pairs, list):
            return []

        return [
            item
            for item in pairs
            if isinstance(item, dict)
        ]

    # =========================================================
    # GECKOTERMINAL NEW-POOL DISCOVERY
    # =========================================================

    async def gecko_new_pool_token_addresses(
        self,
        network: str = "base",
        pages: int = 3,
        retries: int = 2,
    ) -> List[str]:
        """Return token addresses from GeckoTerminal's new-pools feed.

        This is discovery only.  The scanner still obtains the actual
        market pair from DexScreener before applying market/age/security
        gates.  That keeps GeckoTerminal from becoming a second source
        of truth for signal eligibility.
        """

        network = str(network or "").strip().lower()
        if not network or pages <= 0:
            return []

        addresses: List[str] = []
        seen = set()

        for page in range(1, min(int(pages), 5) + 1):
            url = GECKO_NEW_POOLS_URL.format(network=network)

            data = await self._get(
                url,
                params={"page": page},
                retries=retries,
            )

            if not isinstance(data, dict):
                continue

            items = data.get("data")
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                relationships = item.get("relationships") or {}
                if not isinstance(relationships, dict):
                    continue

                for side in ("base_token", "quote_token"):
                    relation = relationships.get(side) or {}
                    if not isinstance(relation, dict):
                        continue

                    token_data = relation.get("data") or {}
                    if not isinstance(token_data, dict):
                        continue

                    token_id = str(
                        token_data.get("id", "") or ""
                    ).strip()

                    # GeckoTerminal IDs are normally network_address.
                    # Only accept EVM-looking addresses here.
                    if "_" in token_id:
                        candidate = token_id.split("_", 1)[1].strip()
                    else:
                        candidate = token_id

                    if not candidate.startswith("0x") or len(candidate) != 42:
                        continue

                    key = candidate.lower()
                    if key in seen:
                        continue

                    seen.add(key)
                    addresses.append(candidate)

        return addresses

    # =========================================================
    # DEDUPLICATION
    # =========================================================

    @staticmethod
    def _pair_key(
        pair: Dict[str, Any],
    ) -> str:

        base = pair.get("baseToken") or {}

        address = str(
            base.get("address", "") or ""
        ).strip().lower()

        pair_address = str(
            pair.get("pairAddress", "") or ""
        ).strip().lower()

        chain_id = str(
            pair.get("chainId", "") or ""
        ).strip().lower()

        return (
            f"{chain_id}:"
            f"{address}:"
            f"{pair_address}"
        )

    # =========================================================
    # GENERIC CHAIN DISCOVERY
    # =========================================================

    async def discover_chain(
        self,
        chain_id: str,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

        chain_id = str(
            chain_id or ""
        ).strip().lower()

        if not chain_id:
            return []

        if queries is None:

            queries = [
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

        # -----------------------------------------------------
        # NORMALIZE QUERY LIST
        # -----------------------------------------------------

        clean_queries = []

        seen_queries = set()

        for query in queries:

            query = str(
                query or ""
            ).strip()

            if not query:
                continue

            key = query.lower()

            if key in seen_queries:
                continue

            seen_queries.add(key)
            clean_queries.append(query)

        # -----------------------------------------------------
        # CHAIN-SPECIFIC DISCOVERY
        #
        # Base receives additional search terms because the
        # generic DexScreener search endpoint is not a complete
        # "new token feed".
        # -----------------------------------------------------

        if chain_id == "base":

            base_extra_queries = [
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
                "aerodrome",
                "degen",
                "higher",
                "brett",
                "toshi",
                "virtual",
                "clanker",
            ]

            for query in base_extra_queries:

                key = query.lower()

                if key not in seen_queries:

                    seen_queries.add(key)
                    clean_queries.append(query)

        all_pairs = []
        seen_pairs = set()

        # =====================================================
        # SEARCH DISCOVERY
        # =====================================================

        for query in clean_queries:

            try:

                pairs = await self.search(query)

            except Exception as exc:

                print(
                    f"❌ Discovery search error "
                    f"for {query}: {exc}"
                )

                continue

            for pair in pairs:

                if not isinstance(pair, dict):
                    continue

                pair_chain = str(
                    pair.get(
                        "chainId",
                        "",
                    )
                ).strip().lower()

                if pair_chain != chain_id:
                    continue

                key = self._pair_key(pair)

                if key in seen_pairs:
                    continue

                seen_pairs.add(key)

                all_pairs.append(pair)

        # =====================================================
        # PROFILE / BOOST DISCOVERY
        # =====================================================

        discovery_calls = await asyncio.gather(
            self.latest_token_profiles(),
            self.latest_boosts(),
            self.top_boosts(),
            return_exceptions=True,
        )

        addresses = set()

        for source in discovery_calls:

            if isinstance(
                source,
                Exception,
            ):

                print(
                    f"⚠️ Discovery source error: "
                    f"{source}"
                )

                continue

            if not isinstance(
                source,
                list,
            ):

                continue

            for item in source:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                item_chain = str(
                    item.get(
                        "chainId",
                        "",
                    )
                ).strip().lower()

                if item_chain != chain_id:
                    continue

                address = str(
                    item.get(
                        "tokenAddress",
                        "",
                    )
                    or ""
                ).strip()

                if address:
                    addresses.add(address)

        # =====================================================
        # GET REAL PAIRS FOR PROFILE/BOOST TOKENS
        # =====================================================

        address_list = list(addresses)

        print(
            f"🔎 Profile/boost {chain_id} "
            f"tokens: {len(address_list)}"
        )

        for start in range(
            0,
            len(address_list),
            30,
        ):

            batch = address_list[
                start:start + 30
            ]

            try:

                pairs = await self.tokens(
                    batch
                )

            except Exception as exc:

                print(
                    f"❌ {chain_id} token "
                    f"discovery error: {exc}"
                )

                continue

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
                ).strip().lower()

                if pair_chain != chain_id:
                    continue

                key = self._pair_key(pair)

                if key in seen_pairs:
                    continue

                seen_pairs.add(key)

                all_pairs.append(pair)

        # =====================================================
        # BASE NEW-POOL FALLBACK DISCOVERY
        # =====================================================
        #
        # DexScreener search is not a guaranteed new-pool feed.  When
        # Base search results are dominated by older pools, supplement
        # discovery with GeckoTerminal's new-pools index.  We only use
        # it to obtain token addresses; DexScreener.tokens() remains
        # the source of pair/market data used by the existing scanner.
        #
        if chain_id == "base":
            try:
                gecko_addresses = await self.gecko_new_pool_token_addresses(
                    network="base",
                    pages=3,
                    retries=2,
                )

                print(
                    f"🦎 Gecko Base new-pool tokens: "
                    f"{len(gecko_addresses)}"
                )

                for start in range(0, len(gecko_addresses), 30):
                    batch = gecko_addresses[start:start + 30]

                    try:
                        gecko_pairs = await self.tokens(batch)
                    except Exception as exc:
                        print(
                            f"⚠️ Gecko Base DexScreener enrichment error: "
                            f"{exc}"
                        )
                        continue

                    for pair in gecko_pairs:
                        if not isinstance(pair, dict):
                            continue

                        pair_chain = str(
                            pair.get("chainId", "") or ""
                        ).strip().lower()

                        if pair_chain != "base":
                            continue

                        key = self._pair_key(pair)
                        if key in seen_pairs:
                            continue

                        seen_pairs.add(key)
                        all_pairs.append(pair)

            except Exception as exc:
                print(
                    f"⚠️ Gecko Base discovery failed: {exc}"
                )

        # =====================================================
        # FINAL DEDUPLICATION
        # =====================================================

        unique_pairs = []

        final_seen = set()

        for pair in all_pairs:

            if not isinstance(pair, dict):
                continue

            key = self._pair_key(pair)

            if key in final_seen:
                continue

            final_seen.add(key)
            unique_pairs.append(pair)

        print(
            f"🔍 {chain_id} discovery pairs: "
            f"{len(unique_pairs)}"
        )

        # =====================================================
        # BASE DIAGNOSTICS
        #
        # This does NOT remove any pair. It only reports how
        # many Base pairs contain usable age information.
        # Scanner.py remains responsible for the hard 48h gate.
        # =====================================================

        if chain_id == "base":

            valid_age_count = 0
            missing_age_count = 0
            old_count = 0

            for pair in unique_pairs:

                created = pair.get(
                    "pairCreatedAt"
                )

                try:

                    created_value = float(
                        created or 0
                    )

                    if created_value > 10_000_000_000:
                        created_value /= 1000.0

                    age = (
                        __import__("time").time()
                        - created_value
                    )

                    if (
                        created_value > 0
                        and 1 <= age <= 48 * 60 * 60
                    ):
                        valid_age_count += 1

                    elif created_value <= 0:
                        missing_age_count += 1

                    elif age > 48 * 60 * 60:
                        old_count += 1

                except (
                    TypeError,
                    ValueError,
                    OverflowError,
                ):

                    missing_age_count += 1

            print(
                "🔵 BASE AGE DISCOVERY: "
                f"valid<=48h={valid_age_count} | "
                f"old>48h={old_count} | "
                f"missing/invalid={missing_age_count}"
            )

        return unique_pairs

    # =========================================================
    # SOLANA DISCOVERY
    # =========================================================

    async def discover_solana(
        self,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

        return await self.discover_chain(
            "solana",
            queries,
        )

    # =========================================================
    # BASE DISCOVERY
    # =========================================================

    async def discover_base(
        self,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

        if queries is None:

            queries = [
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
                "aerodrome",
                "degen",
                "higher",
                "brett",
                "toshi",
                "virtual",
                "clanker",
            ]

        return await self.discover_chain(
            "base",
            queries,
        )

    # =========================================================
    # ROBINHOOD CHAIN DISCOVERY
    # =========================================================

    async def discover_robinhood(
        self,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

        return await self.discover_chain(
            "robinhood",
            queries,
        )

    # =========================================================
    # ARC MAINNET DISCOVERY
    # =========================================================

    async def discover_arc(
        self,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

        return await self.discover_chain(
            "arc",
            queries,
        )
