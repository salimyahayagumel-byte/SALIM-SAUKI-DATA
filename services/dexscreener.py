import asyncio
from typing import Any, Dict, List, Optional

import httpx


SEARCH_URL = (
    "https://api.dexscreener.com/latest/dex/search"
)

TOKEN_PROFILES_URL = (
    "https://api.dexscreener.com/token-profiles/latest/v1"
)

BOOSTS_URL = (
    "https://api.dexscreener.com/token-boosts/latest/v1"
)

TOP_BOOSTS_URL = (
    "https://api.dexscreener.com/token-boosts/top/v1"
)

TOKENS_URL = (
    "https://api.dexscreener.com/latest/dex/tokens"
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

        query = str(
            query or ""
        ).strip()

        if not query:

            return []

        data = await self._get(
            SEARCH_URL,
            params={
                "q": query,
            },
            retries=retries,
        )

        if not isinstance(data, dict):

            return []

        pairs = data.get(
            "pairs",
            [],
        )

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

            address = str(
                address or ""
            ).strip()

            if not address:
                continue

            if address in seen:
                continue

            seen.add(address)

            clean_addresses.append(
                address
            )

        if not clean_addresses:

            return []

        # -----------------------------------------------------
        # DexScreener token endpoint uses addresses in the
        # URL PATH, not as a query parameter.
        #
        # Example:
        #
        # /latest/dex/tokens/ADDRESS1,ADDRESS2
        #
        # -----------------------------------------------------

        joined = ",".join(
            clean_addresses
        )

        url = (
            f"{TOKENS_URL}/"
            f"{joined}"
        )

        data = await self._get(
            url,
            retries=retries,
        )

        if not isinstance(data, dict):

            return []

        pairs = data.get(
            "pairs",
            [],
        )

        if not isinstance(pairs, list):

            return []

        return [
            item
            for item in pairs
            if isinstance(item, dict)
        ]

    # =========================================================
    # SOLANA DISCOVERY
    # =========================================================

    async def discover_solana(
        self,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:

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

        all_pairs = []

        seen_pairs = set()

        # =====================================================
        # SEARCH DISCOVERY
        # =====================================================

        for query in queries:

            try:

                pairs = await self.search(
                    query
                )

            except Exception as exc:

                print(
                    f"❌ Discovery search error "
                    f"for {query}: {exc}"
                )

                continue

            for pair in pairs:

                if not isinstance(pair, dict):

                    continue

                if str(
                    pair.get(
                        "chainId",
                        "",
                    )
                ).lower() != "solana":

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

                pair_address = str(
                    pair.get(
                        "pairAddress",
                        "",
                    )
                    or ""
                ).strip()

                key = (
                    f"{address}:{pair_address}"
                )

                if key in seen_pairs:

                    continue

                seen_pairs.add(
                    key
                )

                all_pairs.append(
                    pair
                )

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

                if str(
                    item.get(
                        "chainId",
                        "",
                    )
                ).lower() != "solana":

                    continue

                address = str(
                    item.get(
                        "tokenAddress",
                        "",
                    )
                    or ""
                ).strip()

                if address:

                    addresses.add(
                        address
                    )

        # =====================================================
        # GET REAL PAIRS FOR DISCOVERED ADDRESSES
        # =====================================================

        address_list = list(
            addresses
        )

        print(
            f"🔎 Profile/boost Solana tokens: "
            f"{len(address_list)}"
        )

        # DexScreener supports batches of token addresses.
        # Keep requests reasonable.
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
                    f"❌ Token discovery error: "
                    f"{exc}"
                )

                continue

            for pair in pairs:

                if not isinstance(
                    pair,
                    dict,
                ):

                    continue

                if str(
                    pair.get(
                        "chainId",
                        "",
                    )
                ).lower() != "solana":

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

                pair_address = str(
                    pair.get(
                        "pairAddress",
                        "",
                    )
                    or ""
                ).strip()

                key = (
                    f"{address}:{pair_address}"
                )

                if key in seen_pairs:

                    continue

                seen_pairs.add(
                    key
                )

                all_pairs.append(
                    pair
                )

        print(
            f"🔍 Solana discovery pairs: "
            f"{len(all_pairs)}"
        )

        return all_pairs
