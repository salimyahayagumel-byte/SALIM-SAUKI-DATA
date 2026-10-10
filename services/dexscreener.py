import asyncio
import os
import random
import time
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

        # DexScreener publishes different limits for different endpoint
        # groups. Keep requests paced locally so cloud/shared-hosting IPs
        # do not burst into 429 responses.
        self.timeout = httpx.Timeout(
            connect=float(os.getenv("DEXSCREENER_CONNECT_TIMEOUT", "20")),
            read=float(os.getenv("DEXSCREENER_READ_TIMEOUT", "40")),
            write=float(os.getenv("DEXSCREENER_WRITE_TIMEOUT", "20")),
            pool=float(os.getenv("DEXSCREENER_POOL_TIMEOUT", "20")),
        )

        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "User-Agent": os.getenv(
                "DEXSCREENER_USER_AGENT",
                "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36 "
                "MASFOX/10.4",
            ),
        }

        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._last_request_at = 0.0
        self._min_request_interval = max(
            0.0,
            float(os.getenv("DEXSCREENER_MIN_REQUEST_INTERVAL", "0.35")),
        )

        self._last_error = ""
        self._last_status = None
        self._last_error_at = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None and not self._client.is_closed:
            return self._client

        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=self.headers,
                    trust_env=False,
                    http2=False,
                )

        return self._client

    async def close(self):
        client = self._client
        self._client = None
        if client is not None and not client.is_closed:
            await client.aclose()

    @property
    def health(self) -> Dict[str, Any]:
        return {
            "status": self._last_status,
            "error": self._last_error,
            "error_at": self._last_error_at or None,
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
        """GET JSON with cloud-friendly connection reuse and backoff.

        429 responses receive a longer backoff because DexScreener documents
        endpoint-specific rate limits.  Other 4xx responses are not retried
        aggressively.  We never bypass blocks or rate limits.
        """

        retries = max(1, int(retries))
        client = await self._get_client()

        for attempt in range(1, retries + 1):
            try:
                async with self._request_lock:
                    now = time.monotonic()
                    wait = self._min_request_interval - (now - self._last_request_at)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last_request_at = time.monotonic()

                    response = await client.get(
                        url,
                        params=params,
                    )

                self._last_status = response.status_code

                if response.status_code == 429:
                    self._last_error = (
                        f"HTTP 429 rate limited: {response.url}"
                    )
                    self._last_error_at = time.time()
                    if attempt < retries:
                        delay = min(
                            30.0,
                            10.0 * attempt + random.uniform(0.5, 2.0),
                        )
                        print(
                            f"⚠️ DexScreener rate limit 429; "
                            f"backing off {delay:.1f}s "
                            f"(attempt {attempt}/{retries})"
                        )
                        await asyncio.sleep(delay)
                        continue

                if response.status_code in {403, 406}:
                    self._last_error = (
                        f"HTTP {response.status_code}: {response.url}"
                    )
                    self._last_error_at = time.time()
                    print(
                        f"⚠️ DexScreener access response "
                        f"{response.status_code}: {response.url}"
                    )
                    # Do not hammer an access-denied response. A later
                    # scan may succeed from a different cloud/network.
                    return None

                response.raise_for_status()

                data = response.json()
                self._last_error = ""
                self._last_error_at = 0.0
                return data

            except httpx.TimeoutException as exc:
                self._last_error = f"timeout: {exc}"
                self._last_error_at = time.time()
                print(
                    f"⚠️ DexScreener timeout "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                self._last_status = status
                self._last_error = (
                    f"HTTP {status}: {exc.response.url}"
                )
                self._last_error_at = time.time()
                print(
                    f"⚠️ DexScreener HTTP error "
                    f"(attempt {attempt}/{retries}): "
                    f"{status} - {exc.response.url}"
                )

            except httpx.RequestError as exc:
                self._last_error = f"connection: {exc}"
                self._last_error_at = time.time()
                print(
                    f"⚠️ DexScreener connection error "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            except Exception as exc:
                self._last_error = f"unexpected: {exc}"
                self._last_error_at = time.time()
                print(
                    f"⚠️ DexScreener unexpected error "
                    f"(attempt {attempt}/{retries}): {exc}"
                )

            if attempt < retries:
                delay = min(
                    12.0,
                    1.5 * (2 ** (attempt - 1)) + random.uniform(0.1, 0.7),
                )
                await asyncio.sleep(delay)

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
                "new base",
                "base launch",
                "aerodrome",
                "degen",
                "brett",
                "toshi",
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
                "new base",
                "base launch",
                "aerodrome",
                "degen",
                "brett",
                "toshi",
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
