import os
import base64
import struct
import asyncio
import json
import time
import httpx


class SecurityChecker:
    """
    Multi-chain token security checker.

    Supported networks:

        🟣 Solana
            - token account exists
            - mint authority
            - freeze authority
            - supply
            - decimals
            - initialization

        🔵 Base / EVM
            - contract exists
            - bytecode exists
            - ERC-20 totalSupply()
            - ERC-20 decimals()
            - ERC-20 symbol()
            - ERC-20 name()
            - basic contract-read validation

    Wannan layer ba ya cewa token 100% safe ne.

    Security score na Base ba cikakken honeypot/audit check ba ne.
    Yana tabbatar da basic on-chain contract information ne.
    """

    # =========================================================
    # SOLANA RPC
    # =========================================================

    DEFAULT_RPC = (
        "https://api.mainnet-beta.solana.com"
    )

    FALLBACK_RPCS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
        "https://rpc.ankr.com/solana",
    ]

    # =========================================================
    # EVM RPC NETWORKS
    # =========================================================

    DEFAULT_BASE_RPC = "https://mainnet.base.org"

    FALLBACK_BASE_RPCS = [
        "https://mainnet.base.org",
        "https://base-rpc.publicnode.com",
    ]

    DEFAULT_ROBINHOOD_RPC = "https://rpc.mainnet.chain.robinhood.com"

    FALLBACK_ROBINHOOD_RPCS = [
        "https://rpc.mainnet.chain.robinhood.com",
    ]

    DEFAULT_ARC_RPC = "https://rpc.mainnet.arc.io"

    FALLBACK_ARC_RPCS = [
        "https://rpc.mainnet.arc.io",
    ]

    # =========================================================
    # RETRIES / TIMEOUTS
    # =========================================================

    MAX_RETRIES = 2

    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 20.0
    WRITE_TIMEOUT = 20.0
    POOL_TIMEOUT = 10.0

    # =========================================================
    # SAFE URL LOGGING
    # =========================================================

    @staticmethod
    def _safe_rpc_url(url):
        """Redact query secrets before writing an RPC URL to logs."""
        text = str(url or "")
        if "?" in text:
            return text.split("?", 1)[0] + "?***HIDDEN***"
        return text

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):

        # =====================================
        # SOLANA CUSTOM RPC
        # =====================================

        custom_rpc = os.getenv(
            "SOLANA_RPC_URL",
            ""
        ).strip()

        # =====================================
        # FLUXRPC
        #
        # FluxRPC is preferred for Solana when a
        # URL or FLUXRPC_API_KEY is configured.
        # Never print the full URL because it may
        # contain the API key in the query string.
        # =====================================

        flux_rpc = os.getenv(
            "FLUXRPC_RPC_URL",
            ""
        ).strip()

        flux_key = os.getenv(
            "FLUXRPC_API_KEY",
            ""
        ).strip()

        if not flux_rpc and flux_key:
            flux_rpc = (
                "https://cdn.fluxrpc.com"
                f"?key={flux_key}"
            )

        # =====================================
        # SOLANA MULTIPLE RPCS
        #
        # Example:
        #
        # SOLANA_RPC_URLS=
        # https://rpc1,https://rpc2
        # =====================================

        custom_rpcs_raw = os.getenv(
            "SOLANA_RPC_URLS",
            ""
        ).strip()

        custom_rpcs = []

        if custom_rpcs_raw:

            custom_rpcs = [
                rpc.strip()
                for rpc in custom_rpcs_raw.split(",")
                if rpc.strip()
            ]

        # =====================================
        # BUILD SOLANA RPC LIST
        # =====================================

        rpc_list = []

        # Prefer FluxRPC when configured.
        if flux_rpc:

            rpc_list.append(
                flux_rpc
            )

        if custom_rpc:

            if custom_rpc not in rpc_list:
                rpc_list.append(
                    custom_rpc
                )

        for rpc in custom_rpcs:

            if rpc not in rpc_list:

                rpc_list.append(
                    rpc
                )

        for rpc in self.FALLBACK_RPCS:

            if rpc not in rpc_list:

                rpc_list.append(
                    rpc
                )

        if not rpc_list:

            rpc_list = [
                self.DEFAULT_RPC
            ]

        self.rpc_urls = rpc_list

        self.rpc_url = self.rpc_urls[0]

        # =====================================
        # BASE CUSTOM RPC
        # =====================================

        custom_base_rpc = os.getenv(
            "BASE_RPC_URL",
            ""
        ).strip()

        # =====================================
        # BASE MULTIPLE RPCS
        #
        # Example:
        #
        # BASE_RPC_URLS=
        # https://rpc1,https://rpc2
        # =====================================

        custom_base_rpcs_raw = os.getenv(
            "BASE_RPC_URLS",
            ""
        ).strip()

        custom_base_rpcs = []

        if custom_base_rpcs_raw:

            custom_base_rpcs = [
                rpc.strip()
                for rpc in custom_base_rpcs_raw.split(",")
                if rpc.strip()
            ]

        # =====================================
        # BUILD BASE RPC LIST
        # =====================================

        base_rpc_list = []

        if custom_base_rpc:

            base_rpc_list.append(
                custom_base_rpc
            )

        for rpc in custom_base_rpcs:

            if rpc not in base_rpc_list:

                base_rpc_list.append(
                    rpc
                )

        for rpc in self.FALLBACK_BASE_RPCS:

            if rpc not in base_rpc_list:

                base_rpc_list.append(
                    rpc
                )

        if not base_rpc_list:

            base_rpc_list = [
                self.DEFAULT_BASE_RPC
            ]

        self.base_rpc_urls = (
            base_rpc_list
        )

        self.base_rpc_url = (
            self.base_rpc_urls[0]
        )

        # =====================================
        # ROBINHOOD / ARC RPC LISTS
        # =====================================
        self.robinhood_rpc_urls = self._build_rpc_list(
            "ROBINHOOD_RPC_URL",
            "ROBINHOOD_RPC_URLS",
            self.FALLBACK_ROBINHOOD_RPCS,
            self.DEFAULT_ROBINHOOD_RPC,
        )
        self.robinhood_rpc_url = self.robinhood_rpc_urls[0]

        self.arc_rpc_urls = self._build_rpc_list(
            "ARC_RPC_URL",
            "ARC_RPC_URLS",
            self.FALLBACK_ARC_RPCS,
            self.DEFAULT_ARC_RPC,
        )
        self.arc_rpc_url = self.arc_rpc_urls[0]

        # Per-chain EVM RPC cooldowns.
        # Keyed by (chain, rpc_url) so Base, Robinhood and Arc
        # maintain independent rate-limit state.
        self._evm_rpc_cooldowns = {}

        # =====================================
        # BASE HONEYPOT SECURITY
        #
        # Configurable through environment variables.
        # Base can fail closed when the external simulation
        # is required but unavailable. Robinhood and Arc
        # do not use the Base honeypot requirement.
        # =====================================
        self.base_honeypot_enabled = (
            os.getenv("BASE_HONEYPOT_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self.base_honeypot_required = (
            os.getenv("BASE_HONEYPOT_REQUIRED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        try:
            self.base_honeypot_timeout = float(
                os.getenv("BASE_HONEYPOT_TIMEOUT", "15")
            )
        except (TypeError, ValueError):
            self.base_honeypot_timeout = 15.0

        try:
            self.base_honeypot_cache_seconds = float(
                os.getenv("BASE_HONEYPOT_CACHE_SECONDS", "300")
            )
        except (TypeError, ValueError):
            self.base_honeypot_cache_seconds = 300.0

        self._base_honeypot_cache = {}


    def _build_rpc_list(self, single_env, multi_env, fallbacks, default):
        values = []
        single = os.getenv(single_env, "").strip()
        multi = os.getenv(multi_env, "").strip()
        if single:
            values.append(single)
        if multi:
            values.extend(
                item.strip() for item in multi.split(",") if item.strip()
            )
        values.extend(fallbacks)
        if not values:
            values.append(default)
        result = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    # =========================================================
    # SOLANA RPC REQUEST
    # =========================================================

    async def _rpc(
        self,
        method,
        params
    ):
        """
        Send Solana JSON-RPC request.

        Yana:
            1. Retry RPC.
            2. Gwada fallback RPC.
            3. Return valid JSON result.
            4. Return None idan duk sun kasa.
        """

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        timeout = httpx.Timeout(
            timeout=self.READ_TIMEOUT,
            connect=self.CONNECT_TIMEOUT,
            read=self.READ_TIMEOUT,
            write=self.WRITE_TIMEOUT,
            pool=self.POOL_TIMEOUT,
        )

        last_error = None

        # Per-endpoint cooldown prevents a dead/unstable RPC from
        # being hammered every scan while healthy fallbacks continue.
        if not hasattr(self, "_rpc_cooldowns"):
            self._rpc_cooldowns = {}

        loop = asyncio.get_running_loop()
        now = loop.time()
        cooldown_seconds = 45.0

        ordered_rpcs = []
        if self.rpc_url:
            ordered_rpcs.append(self.rpc_url)
        for rpc_url in self.rpc_urls:
            if rpc_url not in ordered_rpcs:
                ordered_rpcs.append(rpc_url)

        available_rpcs = [
            rpc_url for rpc_url in ordered_rpcs
            if now >= self._rpc_cooldowns.get(rpc_url, 0.0)
        ]

        if not available_rpcs:
            available_rpcs = ordered_rpcs

        # =====================================
        # TRY EVERY SOLANA RPC
        # =====================================

        for rpc_index, rpc_url in enumerate(
            available_rpcs,
            start=1
        ):

            for attempt in range(
                1,
                self.MAX_RETRIES + 1
            ):

                try:

                    async with httpx.AsyncClient(
                        timeout=timeout,
                        follow_redirects=True,
                    ) as client:

                        response = await client.post(
                            rpc_url,
                            json=payload,
                            headers={
                                "Content-Type":
                                    "application/json",
                            },
                        )

                        response.raise_for_status()

                        data = response.json()

                        # =================================
                        # JSON-RPC ERROR
                        # =================================

                        if data.get("error"):

                            error = data.get(
                                "error"
                            )

                            last_error = (
                                f"RPC returned error: "
                                f"{error}"
                            )

                            print(
                                f"⚠️ Solana RPC #{rpc_index} "
                                f"attempt {attempt}: "
                                f"{last_error}"
                            )

                            break

                        # =================================
                        # VALID RESPONSE
                        # =================================

                        if data.get(
                            "jsonrpc"
                        ) == "2.0":

                            self.rpc_url = rpc_url

                            print(
                                f"✅ Solana RPC OK: "
                                f"endpoint #{rpc_index} | "
                                f"{self._safe_rpc_url(rpc_url)}"
                            )

                            return data

                        last_error = (
                            "INVALID JSON-RPC RESPONSE"
                        )

                        print(
                            f"⚠️ Solana RPC #{rpc_index} "
                            f"attempt {attempt}: "
                            f"{last_error}"
                        )

                except (
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                    httpx.ConnectError,
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                ) as exc:

                    last_error = repr(exc)

                    # Short circuit repeated failures for this endpoint.
                    self._rpc_cooldowns[rpc_url] = (
                        loop.time() + cooldown_seconds
                    )

                    print(
                        f"⚠️ Solana RPC #{rpc_index} "
                        f"attempt {attempt} TIMEOUT/NETWORK | "
                        f"endpoint={self._safe_rpc_url(rpc_url)}"
                    )

                except Exception as exc:

                    last_error = repr(exc)

                    print(
                        f"⚠️ Solana RPC #{rpc_index} "
                        f"attempt {attempt}: "
                        f"{exc}"
                    )

                # =================================
                # SMALL RETRY DELAY
                # =================================

                if attempt < self.MAX_RETRIES:

                    await asyncio.sleep(
                        0.5 * attempt
                    )

        print(
            "❌ All Solana RPC endpoints failed."
        )

        if last_error:

            print(
                "Last Solana RPC error:",
                last_error
            )

        return None

    # =========================================================
    # BASE / EVM RPC REQUEST
    # =========================================================

    async def _base_rpc(
        self,
        method,
        params,
        chain="base",
    ):
        """
        Send Base/EVM JSON-RPC request.

        V6 RPC strategy:

            - Try active RPC first.
            - HTTP 429 = rate limited.
            - Do NOT retry a rate-limited RPC.
            - Immediately move to the next RPC.
            - Temporary cooldown prevents repeated 429 requests.
            - Network/server errors may still retry.
        """

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        timeout = httpx.Timeout(
            timeout=self.READ_TIMEOUT,
            connect=self.CONNECT_TIMEOUT,
            read=self.READ_TIMEOUT,
            write=self.WRITE_TIMEOUT,
            pool=self.POOL_TIMEOUT,
        )

        last_error = None

        # Human-readable chain label used by RPC logs.
        rpc_label = str(chain or "evm").upper()

        # =====================================
        # EVM RPC RATE-LIMIT COOLDOWN
        # =====================================

        if not hasattr(
            self,
            "_evm_rpc_cooldowns"
        ):

            self._evm_rpc_cooldowns = {}

        cooldown_seconds = 60.0

        now = asyncio.get_running_loop().time()

        # =====================================
        # BUILD ORDERED RPC LIST
        #
        # Active RPC first.
        # Rate-limited RPCs are skipped.
        # =====================================

        ordered_rpcs = []

        # Select the RPC pool that belongs to the requested EVM chain.
        # Base, Robinhood and Arc must never share RPC endpoints.
        chain_key = str(chain or "base").lower().strip()

        if chain_key == "robinhood":
            active_rpc = self.robinhood_rpc_url
            chain_rpc_urls = self.robinhood_rpc_urls
        elif chain_key == "arc":
            active_rpc = self.arc_rpc_url
            chain_rpc_urls = self.arc_rpc_urls
        else:
            active_rpc = self.base_rpc_url
            chain_rpc_urls = self.base_rpc_urls

        if active_rpc:
            ordered_rpcs.append(active_rpc)

        for rpc_url in chain_rpc_urls:
            if rpc_url not in ordered_rpcs:
                ordered_rpcs.append(rpc_url)

        available_rpcs = []

        for rpc_url in ordered_rpcs:

            cooldown_until = (
                self._evm_rpc_cooldowns.get(
                    (chain_key, rpc_url),
                    0.0
                )
            )

            if now < cooldown_until:

                remaining = (
                    cooldown_until - now
                )

                print(
                    f"⏳ {rpc_label} RPC cooldown: "
                    f"{rpc_url} "
                    f"({remaining:.1f}s)"
                )

                continue

            available_rpcs.append(
                rpc_url
            )

        # =====================================
        # IF ALL RPCS ARE IN COOLDOWN
        #
        # Try the first configured RPC anyway.
        # =====================================

        if not available_rpcs:

            available_rpcs = ordered_rpcs

        # =====================================
        # TRY BASE RPC ENDPOINTS
        # =====================================

        for rpc_index, rpc_url in enumerate(
            available_rpcs,
            start=1
        ):

            for attempt in range(
                1,
                self.MAX_RETRIES + 1
            ):

                try:

                    async with httpx.AsyncClient(
                        timeout=timeout,
                        follow_redirects=True,
                    ) as client:

                        response = await client.post(
                            rpc_url,
                            json=payload,
                            headers={
                                "Content-Type":
                                    "application/json",
                            },
                        )

                        # =================================
                        # HTTP RATE LIMIT
                        # =================================

                        if response.status_code == 429:

                            self._evm_rpc_cooldowns[
                                (chain_key, rpc_url)
                            ] = (
                                now +
                                cooldown_seconds
                            )

                            last_error = (
                                "HTTP 429 RATE LIMITED"
                            )

                            print(
                                f"⚠️ {rpc_label} RPC #{rpc_index} "
                                f"RATE LIMITED (429): "
                                f"{self._safe_rpc_url(rpc_url)}"
                            )

                            # Do NOT retry this RPC.
                            break

                        response.raise_for_status()

                        data = response.json()

                        # =================================
                        # JSON-RPC ERROR
                        # =================================

                        if data.get("error"):

                            error = data.get(
                                "error"
                            )

                            last_error = (
                                f"Base RPC returned error: "
                                f"{error}"
                            )

                            print(
                                f"⚠️ {rpc_label} RPC #{rpc_index} "
                                f"attempt {attempt}: "
                                f"{last_error}"
                            )

                            # Move to next RPC.
                            break

                        # =================================
                        # VALID RESPONSE
                        # =================================

                        if data.get(
                            "jsonrpc"
                        ) == "2.0":

                            # Remember the successful endpoint for this chain.
                            if chain_key == "robinhood":
                                self.robinhood_rpc_url = rpc_url
                            elif chain_key == "arc":
                                self.arc_rpc_url = rpc_url
                            else:
                                self.base_rpc_url = rpc_url

                            # Clear old cooldown after
                            # successful recovery.
                            self._evm_rpc_cooldowns.pop(
                                (chain_key, rpc_url),
                                None
                            )

                            print(
                                f"✅ {rpc_label} RPC OK: "
                                f"{self._safe_rpc_url(rpc_url)}"
                            )

                            return data

                        last_error = (
                            "INVALID JSON-RPC RESPONSE"
                        )

                        print(
                            f"⚠️ {rpc_label} RPC #{rpc_index} "
                            f"attempt {attempt}: "
                            f"{last_error}"
                        )

                except (
                    httpx.ConnectTimeout,
                    httpx.ReadTimeout,
                    httpx.WriteTimeout,
                    httpx.PoolTimeout,
                    httpx.ConnectError,
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                ) as exc:

                    last_error = repr(exc)

                    print(
                        f"⚠️ {rpc_label} RPC #{rpc_index} "
                        f"attempt {attempt} "
                        f"TIMEOUT/NETWORK:"
                        f" {rpc_url}"
                    )

                except Exception as exc:

                    last_error = repr(exc)

                    print(
                        f"⚠️ {rpc_label} RPC #{rpc_index} "
                        f"attempt {attempt}: "
                        f"{exc}"
                    )

                # =================================
                # RETRY DELAY
                #
                # Only for non-429 errors.
                # =================================

                if attempt < self.MAX_RETRIES:

                    await asyncio.sleep(
                        0.5 * attempt
                    )

        print(
            f"❌ All {rpc_label} RPC endpoints failed."
        )

        if last_error:

            print(
                f"Last {rpc_label} RPC error:",
                last_error
            )

        return None

    # =========================================================
    # GET SOLANA MINT ACCOUNT
    # =========================================================

    async def get_mint_account(
        self,
        address
    ):
        """
        Get raw mint account data from Solana RPC.
        """

        data = await self._rpc(
            "getAccountInfo",
            [
                address,
                {
                    "encoding": "base64",
                    "commitment": "confirmed",
                },
            ],
        )

        if not data:

            return None

        result = data.get(
            "result"
        ) or {}

        value = result.get(
            "value"
        )

        if not value:

            return None

        return value

    # =========================================================
    # PARSE SPL MINT DATA
    # =========================================================

    @staticmethod
    def parse_mint_data(
        account
    ):
        """
        Parse SPL Token Mint layout.

        SPL Token Mint layout:

        offset 0:
            mint_authority_option u32

        offset 4:
            mint_authority pubkey 32 bytes

        offset 36:
            supply u64

        offset 44:
            decimals u8

        offset 45:
            is_initialized bool u8

        offset 46:
            freeze_authority_option u32

        offset 50:
            freeze_authority pubkey 32 bytes
        """

        try:

            data_field = account.get(
                "data"
            )

            if not data_field:

                return None

            if not isinstance(
                data_field,
                list
            ):

                return None

            if len(data_field) < 1:

                return None

            encoded = data_field[0]

            if not encoded:

                return None

            raw = base64.b64decode(
                encoded
            )

            # =================================
            # SPL MINT = 82 BYTES
            # =================================

            if len(raw) < 82:

                print(
                    "⚠️ Mint account too short:",
                    len(raw)
                )

                return None

            # =================================
            # MINT AUTHORITY
            # =================================

            mint_option = struct.unpack_from(
                "<I",
                raw,
                0
            )[0]

            mint_authority = None

            if mint_option == 1:

                mint_authority = raw[
                    4:36
                ].hex()

            # =================================
            # SUPPLY
            # =================================

            supply = struct.unpack_from(
                "<Q",
                raw,
                36
            )[0]

            # =================================
            # DECIMALS
            # =================================

            decimals = raw[44]

            # =================================
            # INITIALIZED
            # =================================

            initialized = bool(
                raw[45]
            )

            # =================================
            # FREEZE AUTHORITY
            # =================================

            freeze_option = struct.unpack_from(
                "<I",
                raw,
                46
            )[0]

            freeze_authority = None

            if freeze_option == 1:

                freeze_authority = raw[
                    50:82
                ].hex()

            return {
                "mint_authority":
                    mint_authority,

                "mint_authority_enabled":
                    mint_option == 1,

                "freeze_authority":
                    freeze_authority,

                "freeze_authority_enabled":
                    freeze_option == 1,

                "supply":
                    supply,

                "decimals":
                    decimals,

                "initialized":
                    initialized,
            }

        except Exception as exc:

            print(
                "❌ Mint parser error:",
                exc
            )

            return None

    # =========================================================
    # EVM ADDRESS VALIDATION
    # =========================================================

    @staticmethod
    def is_evm_address(
        address
    ):

        if not address:

            return False

        address = str(
            address
        ).strip()

        if not address.startswith(
            "0x"
        ):

            return False

        if len(address) != 42:

            return False

        try:

            int(
                address[2:],
                16
            )

            return True

        except (
            TypeError,
            ValueError,
        ):

            return False

    # =========================================================
    # EVM UINT DECODER
    # =========================================================

    @staticmethod
    def decode_uint256(
        value
    ):

        try:

            if not value:

                return None

            value = str(
                value
            ).strip()

            if value.startswith(
                "0x"
            ):

                value = value[2:]

            if not value:

                return 0

            return int(
                value,
                16
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

    # =========================================================
    # EVM STRING DECODER
    # =========================================================

    @staticmethod
    def decode_erc20_string(
        value
    ):

        try:

            if not value:

                return None

            raw = bytes.fromhex(
                str(value)[2:]
                if str(value).startswith("0x")
                else str(value)
            )

            if not raw:

                return None

            # =================================
            # ABI dynamic string:
            #
            # offset 32
            # length 32
            # string bytes
            # =================================

            if len(raw) >= 64:

                offset = int.from_bytes(
                    raw[0:32],
                    "big"
                )

                if (
                    offset >= 0
                    and
                    offset + 32 <= len(raw)
                ):

                    length = int.from_bytes(
                        raw[
                            offset:
                            offset + 32
                        ],
                        "big"
                    )

                    start = (
                        offset + 32
                    )

                    end = (
                        start + length
                    )

                    if (
                        end <= len(raw)
                    ):

                        decoded = raw[
                            start:end
                        ].decode(
                            "utf-8",
                            errors="ignore"
                        ).strip(
                            "\x00"
                        )

                        if decoded:

                            return decoded

            # =================================
            # bytes32 fallback
            # =================================

            decoded = raw.decode(
                "utf-8",
                errors="ignore"
            ).strip(
                "\x00"
            )

            if decoded:

                return decoded

            return None

        except Exception:

            return None

    # =========================================================
    # BASE CONTRACT CODE
    # =========================================================

    async def get_base_contract_code(
        self,
        address,
        chain="base",
    ):

        if not self.is_evm_address(
            address
        ):

            return None

        data = await self._base_rpc(
            "eth_getCode",
            [
                address,
                "latest",
            ],
            chain=chain,
        )

        if not data:

            return None

        return (
            data.get(
                "result"
            )
        )

    # =========================================================
    # BASE ETH CALL
    # =========================================================

    async def base_eth_call(
        self,
        address,
        data,
        chain="base",
    ):

        if not self.is_evm_address(
            address
        ):

            return None

        response = await self._base_rpc(
            "eth_call",
            [
                {
                    "to": address,
                    "data": data,
                },
                "latest",
            ],
            chain=chain,
        )

        if not response:

            return None

        if response.get(
            "error"
        ):

            return None

        return response.get(
            "result"
        )

    # =========================================================
    # BASE ERC-20 METADATA
    # =========================================================

    async def get_base_erc20_metadata(
        self,
        address,
        chain="base",
    ):
        """
        Standard ERC-20 calls:

            name()
            symbol()
            decimals()
            totalSupply()
        """

        # =====================================
        # ERC-20 SELECTORS
        # =====================================

        NAME_SELECTOR = (
            "0x06fdde03"
        )

        SYMBOL_SELECTOR = (
            "0x95d89b41"
        )

        DECIMALS_SELECTOR = (
            "0x313ce567"
        )

        TOTAL_SUPPLY_SELECTOR = (
            "0x18160ddd"
        )

        # =====================================
        # CALLS
        # =====================================

        name_raw = await self.base_eth_call(
            address,
            NAME_SELECTOR,
            chain=chain,
        )

        symbol_raw = await self.base_eth_call(
            address,
            SYMBOL_SELECTOR,
            chain=chain,
        )

        decimals_raw = await self.base_eth_call(
            address,
            DECIMALS_SELECTOR,
            chain=chain,
        )

        supply_raw = await self.base_eth_call(
            address,
            TOTAL_SUPPLY_SELECTOR,
            chain=chain,
        )

        # =====================================
        # DECODE
        # =====================================

        name = self.decode_erc20_string(
            name_raw
        )

        symbol = self.decode_erc20_string(
            symbol_raw
        )

        decimals = self.decode_uint256(
            decimals_raw
        )

        supply = self.decode_uint256(
            supply_raw
        )

        return {
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "supply": supply,
            "name_read": bool(
                name_raw
            ),
            "symbol_read": bool(
                symbol_raw
            ),
            "decimals_read": (
                decimals is not None
            ),
            "supply_read": (
                supply is not None
            ),
        }

    # =========================================================
    # BASE HONEYPOT CHECK
    # =========================================================

    async def check_base_honeypot(
        self,
        token,
    ):
        """Run a lightweight Honeypot.is simulation for Base tokens.

        Honeypot.is currently documents the v2 IsHoneypot endpoint as
        unauthenticated. We treat this as a security signal, not as an
        absolute guarantee, and cache successful/failed responses briefly
        to avoid hammering the service on every scan.
        """

        if not self.base_honeypot_enabled:
            return {"available": False, "enabled": False}

        address = str(token.get("address", "") or "").strip()
        pair = str(token.get("pair", "") or "").strip()
        if not self.is_evm_address(address):
            return {"available": False, "enabled": True, "error": "INVALID_ADDRESS"}

        now = time.time()
        cached = self._base_honeypot_cache.get(address)
        if cached and now - cached.get("timestamp", 0) < self.base_honeypot_cache_seconds:
            return dict(cached.get("data", {}))

        params = {
            "address": address,
            "chainID": 8453,
        }
        if self.is_evm_address(pair):
            params["pair"] = pair

        url = "https://api.honeypot.is/v2/IsHoneypot"

        try:
            timeout = httpx.Timeout(
                self.base_honeypot_timeout,
                connect=min(10.0, self.base_honeypot_timeout),
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError("Invalid Honeypot response")

            summary = payload.get("summary") or {}
            simulation = payload.get("simulationResult") or {}
            honeypot = payload.get("honeypotResult") or {}
            contract_code = payload.get("contractCode") or {}

            risk_level = summary.get("riskLevel")
            try:
                risk_level = int(risk_level) if risk_level is not None else None
            except (TypeError, ValueError):
                risk_level = None

            buy_tax = simulation.get("buyTax")
            sell_tax = simulation.get("sellTax")
            try:
                buy_tax = float(buy_tax) if buy_tax is not None else None
            except (TypeError, ValueError):
                buy_tax = None
            try:
                sell_tax = float(sell_tax) if sell_tax is not None else None
            except (TypeError, ValueError):
                sell_tax = None

            data = {
                "available": True,
                "enabled": True,
                "risk": summary.get("risk", "unknown"),
                "risk_level": risk_level,
                "is_honeypot": bool(honeypot.get("isHoneypot")) if "isHoneypot" in honeypot else None,
                "honeypot_reason": honeypot.get("honeypotReason"),
                "simulation_success": payload.get("simulationSuccess"),
                "buy_tax": buy_tax,
                "sell_tax": sell_tax,
                "contract_open_source": contract_code.get("openSource"),
                "root_open_source": contract_code.get("rootOpenSource"),
                "is_proxy": contract_code.get("isProxy"),
                "has_proxy_calls": contract_code.get("hasProxyCalls"),
                "flags": payload.get("flags") or summary.get("flags") or [],
            }

            self._base_honeypot_cache[address] = {
                "timestamp": now,
                "data": data,
            }
            return data

        except Exception as exc:
            data = {
                "available": False,
                "enabled": True,
                "error": str(exc),
            }
            self._base_honeypot_cache[address] = {
                "timestamp": now,
                "data": data,
            }
            print(
                f"⚠️ Base Honeypot check unavailable for {address}: {exc}"
            )
            return data

    # =========================================================
    # BASE SECURITY CHECK
    # =========================================================

    async def check_base(
        self,
        token
    ):
        """
        Basic Base/EVM token security check.

        Wannan ba honeypot simulator ba ne kuma
        ba full smart-contract audit ba ne.

        Yana duba:

            - valid EVM address
            - contract bytecode exists
            - ERC-20 metadata
            - total supply
            - decimals
        """

        chain = str(token.get("chain", "base") or "base").lower().strip()
        if chain not in ("base", "robinhood", "arc"):
            chain = "base"

        address = str(
            token.get(
                "address",
                ""
            )
            or ""
        ).strip()

        # =====================================
        # ADDRESS CHECK
        # =====================================

        if not self.is_evm_address(
            address
        ):

            return {
                "security_score": 0,
                "security_status": "FAIL",
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
                    "INVALID EVM TOKEN ADDRESS"
                ],

                "contract_exists": False,
                "bytecode_exists": False,
                "erc20_metadata_valid": False,
                "security_chain": "base",
            }

        # =====================================
        # CONTRACT CODE
        # =====================================

        try:

            if chain == "base":
                code = await self.get_base_contract_code(address)
            else:
                code = await self.get_base_contract_code(
                    address,
                    chain=chain,
                )

        except Exception as exc:

            print(
                f"❌ {chain.upper()} contract check error "
                f"for {address}: {exc}"
            )

            code = None

        if code is None:

            return {
                "security_score": 0,
                "security_status": "RPC ERROR",
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
                    "COULD NOT READ EVM CONTRACT"
                ],

                "contract_exists": False,
                "bytecode_exists": False,
                "erc20_metadata_valid": False,
                "security_chain": "base",
            }

        # =====================================
        # CONTRACT EXISTENCE
        # =====================================

        bytecode_exists = (
            isinstance(
                code,
                str
            )
            and
            code not in (
                "",
                "0x",
                "0X",
            )
        )

        if not bytecode_exists:

            return {
                "security_score": 0,
                "security_status": "FAIL",
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
                    "NO EVM CONTRACT BYTECODE FOUND"
                ],

                "contract_exists": False,
                "bytecode_exists": False,
                "erc20_metadata_valid": False,
                "security_chain": "base",
            }

        # =====================================
        # ERC-20 METADATA
        # =====================================

        try:

            metadata = (
                (
                    await self.get_base_erc20_metadata(address)
                    if chain == "base"
                    else await self.get_base_erc20_metadata(
                        address,
                        chain=chain,
                    )
                )
            )

        except Exception as exc:

            print(
                f"❌ Base ERC-20 metadata error "
                f"for {address}: {exc}"
            )

            metadata = {
                "name": None,
                "symbol": None,
                "decimals": None,
                "supply": None,
                "name_read": False,
                "symbol_read": False,
                "decimals_read": False,
                "supply_read": False,
            }

        # =====================================
        # METADATA VALIDATION
        # =====================================

        metadata_reads = 0

        if metadata.get(
            "name_read"
        ):

            metadata_reads += 1

        if metadata.get(
            "symbol_read"
        ):

            metadata_reads += 1

        if metadata.get(
            "decimals_read"
        ):

            metadata_reads += 1

        if metadata.get(
            "supply_read"
        ):

            metadata_reads += 1

        erc20_metadata_valid = (
            metadata_reads >= 2
        )

        # =====================================
        # HONEYPOT / TRADE SIMULATION
        # =====================================

        honeypot = (
            await self.check_base_honeypot(token)
            if chain == "base"
            else {
                "available": False,
                "enabled": False,
                "reason": "EXTERNAL HONEYPOT SIMULATION NOT CONFIGURED FOR THIS CHAIN",
            }
        )

        # =====================================
        # SCORE
        # =====================================

        score = 50

        reasons = []

        # Contract exists
        score += 20

        reasons.append(
            "EVM CONTRACT EXISTS"
        )

        # Bytecode
        if bytecode_exists:

            reasons.append(
                "CONTRACT BYTECODE FOUND"
            )

        # =====================================
        # ERC-20 METADATA
        # =====================================

        if metadata.get(
            "name_read"
        ):

            score += 5

            reasons.append(
                "ERC-20 NAME READABLE"
            )

        else:

            reasons.append(
                "ERC-20 NAME NOT READABLE"
            )

        if metadata.get(
            "symbol_read"
        ):

            score += 5

            reasons.append(
                "ERC-20 SYMBOL READABLE"
            )

        else:

            reasons.append(
                "ERC-20 SYMBOL NOT READABLE"
            )

        # =====================================
        # DECIMALS
        # =====================================

        decimals = metadata.get(
            "decimals"
        )

        if decimals is not None:

            if 0 <= decimals <= 36:

                score += 10

                reasons.append(
                    "ERC-20 DECIMALS VALID"
                )

            else:

                score -= 10

                reasons.append(
                    "ERC-20 DECIMALS UNUSUAL"
                )

        else:

            reasons.append(
                "DECIMALS COULD NOT BE READ"
            )

        # =====================================
        # TOTAL SUPPLY
        # =====================================

        supply = metadata.get(
            "supply"
        )

        if supply is not None:

            if supply > 0:

                score += 10

                reasons.append(
                    "TOTAL SUPPLY READABLE"
                )

            else:

                score -= 10

                reasons.append(
                    "TOTAL SUPPLY IS ZERO"
                )

        else:

            reasons.append(
                "TOTAL SUPPLY COULD NOT BE READ"
            )

        # =====================================
        # HONEYPOT RISK
        # =====================================

        if honeypot.get("available"):

            risk_level = honeypot.get("risk_level")
            is_honeypot = honeypot.get("is_honeypot")
            simulation_success = honeypot.get("simulation_success")

            if is_honeypot is True:
                score = 0
                reasons.append("HONEYPOT DETECTED")

            elif risk_level is not None:
                # Honeypot riskLevel is documented as 0..100. Convert it
                # into a security contribution without allowing the basic
                # contract checks to masquerade as full security.
                score = min(score, max(0, 100 - risk_level))
                reasons.append(
                    f"HONEYPOT RISK LEVEL {risk_level}"
                )

                if risk_level <= 19:
                    reasons.append("LOW HONEYPOT RISK")
                elif risk_level <= 59:
                    reasons.append("MEDIUM HONEYPOT RISK")
                else:
                    reasons.append("HIGH HONEYPOT RISK")

            if simulation_success is True:
                reasons.append("BUY/SELL SIMULATION COMPLETED")
            elif simulation_success is False:
                score = min(score, 70)
                reasons.append("BUY/SELL SIMULATION FAILED")

            buy_tax = honeypot.get("buy_tax")
            sell_tax = honeypot.get("sell_tax")
            if buy_tax is not None and buy_tax > 10:
                score = min(score, 75)
                reasons.append(f"HIGH BUY TAX {buy_tax:.1f}%")
            if sell_tax is not None and sell_tax > 10:
                score = min(score, 75)
                reasons.append(f"HIGH SELL TAX {sell_tax:.1f}%")

            if honeypot.get("root_open_source") is False:
                score = min(score, 75)
                reasons.append("ROOT CONTRACT NOT OPEN SOURCE")

            if honeypot.get("has_proxy_calls") is True:
                score = min(score, 85)
                reasons.append("PROXY CALLS DETECTED")

        elif self.base_honeypot_required:
            # Fail closed when the stronger Base security layer is required
            # but the external simulation could not be reached.
            score = min(score, 69)
            reasons.append("HONEYPOT CHECK UNAVAILABLE")

        # =====================================
        # SCORE BOUNDS
        # =====================================

        score = max(
            0,
            min(
                score,
                100
            )
        )

        # =====================================
        # STATUS
        # =====================================

        if score >= 90:

            status = "🟢 PASS"

        elif score >= 69:

            status = "🟢 PASS"

        else:

            status = "🔴 FAIL"

        # =====================================
        # FINAL DECISION
        #
        # NOTE:
        #
        # Base security here means basic
        # contract validation only.
        #
        # Do not claim full safety.
        # =====================================

        should_pass = (
            score >= 69
            and bytecode_exists
            and erc20_metadata_valid
            and supply is not None
            and supply > 0
            and decimals is not None
            and 0 <= decimals <= 36
            and (
                chain != "base"
                or not self.base_honeypot_required
                or bool(honeypot.get("available"))
            )
            and honeypot.get("is_honeypot") is not True
            and honeypot.get("simulation_success") is not False
        )

        # =====================================
        # RETURN
        # =====================================

        return {

            "security_score":
                score,

            "security_status":
                status,

            "should_pass":
                should_pass,

            # These are Solana-specific.
            # Keep fields for scanner compatibility.
            "mint_authority":
                None,

            "freeze_authority":
                None,

            "mint_authority_enabled":
                None,

            "freeze_authority_enabled":
                None,

            "supply":
                supply,

            "decimals":
                decimals,

            "security_reasons":
                reasons,

            # Base-specific fields
            "contract_exists":
                True,

            "bytecode_exists":
                bytecode_exists,

            "erc20_metadata_valid":
                erc20_metadata_valid,

            "erc20_name":
                metadata.get(
                    "name"
                ),

            "erc20_symbol":
                metadata.get(
                    "symbol"
                ),

            "security_chain":
                chain,

            "honeypot_check": honeypot,
            "honeypot_available": bool(honeypot.get("available")),
            "honeypot_risk": honeypot.get("risk"),
            "honeypot_risk_level": honeypot.get("risk_level"),
            "honeypot_detected": honeypot.get("is_honeypot"),
            "buy_tax": honeypot.get("buy_tax"),
            "sell_tax": honeypot.get("sell_tax"),
            "contract_open_source": honeypot.get("root_open_source"),
            "proxy_calls": honeypot.get("has_proxy_calls"),
        }

    # =========================================================
    # SECURITY CHECK
    # =========================================================

    async def check(
        self,
        token
    ):
        """
        Run security check for one token.

        Chain routing:

            solana -> Solana SPL security

            base/robinhood/arc -> EVM security
        """

        chain = str(
            token.get(
                "chain",
                ""
            )
        ).lower()

        # =====================================
        # BASE
        # =====================================

        if chain in ("base", "robinhood", "arc"):

            return await self.check_base(
                token
            )

        # =====================================
        # ONLY SUPPORTED CHAINS
        # =====================================

        if chain != "solana":

            return {
                "security_score": 0,
                "security_status": "UNSUPPORTED",
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
                    "UNSUPPORTED BLOCKCHAIN"
                ],
            }

        address = token.get(
            "address"
        )

        # =====================================
        # ADDRESS CHECK
        # =====================================

        if not address:

            return {
                "security_score": 0,
                "security_status": "FAIL",
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
                    "NO TOKEN ADDRESS"
                ],
            }

        # =====================================
        # GET MINT ACCOUNT
        # =====================================

        account = await self.get_mint_account(
            address
        )

        if not account:

            return {
                "security_score": 0,
                "security_status": "RPC ERROR",
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
                    "COULD NOT READ "
                    "SOLANA MINT ACCOUNT"
                ],
            }

        # =====================================
        # PARSE
        # =====================================

        parsed = self.parse_mint_data(
            account
        )

        if not parsed:

            return {
                "security_score": 0,
                "security_status": "PARSE ERROR",
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
                    "INVALID OR UNSUPPORTED "
                    "MINT DATA"
                ],
            }

        # =====================================
        # INITIAL SCORE
        # =====================================

        score = 100

        reasons = []

        # =====================================
        # MINT AUTHORITY
        # =====================================

        if parsed[
            "mint_authority_enabled"
        ]:

            score -= 35

            reasons.append(
                "MINT AUTHORITY ENABLED"
            )

        else:

            reasons.append(
                "MINT AUTHORITY REVOKED"
            )

        # =====================================
        # FREEZE AUTHORITY
        # =====================================

        if parsed[
            "freeze_authority_enabled"
        ]:

            score -= 35

            reasons.append(
                "FREEZE AUTHORITY ENABLED"
            )

        else:

            reasons.append(
                "FREEZE AUTHORITY REVOKED"
            )

        # =====================================
        # INITIALIZATION
        # =====================================

        if not parsed[
            "initialized"
        ]:

            score -= 50

            reasons.append(
                "MINT NOT INITIALIZED"
            )

        else:

            reasons.append(
                "MINT INITIALIZED"
            )

        # =====================================
        # SCORE BOUNDS
        # =====================================

        score = max(
            0,
            min(
                score,
                100
            )
        )

        # =====================================
        # STATUS
        # =====================================

        if score >= 90:

            status = "🟢 PASS"

        elif score >= 69:

            status = "🟢 PASS"

        else:

            status = "🔴 FAIL"

        # =====================================
        # FINAL SECURITY DECISION
        # =====================================

        should_pass = (
            score >= 69
            and not parsed[
                "mint_authority_enabled"
            ]
            and not parsed[
                "freeze_authority_enabled"
            ]
            and parsed[
                "initialized"
            ]
        )

        # =====================================
        # RETURN
        # =====================================

        return {
            "security_score":
                score,

            "security_status":
                status,

            "should_pass":
                should_pass,

            "mint_authority":
                parsed[
                    "mint_authority"
                ],

            "freeze_authority":
                parsed[
                    "freeze_authority"
                ],

            "mint_authority_enabled":
                parsed[
                    "mint_authority_enabled"
                ],

            "freeze_authority_enabled":
                parsed[
                    "freeze_authority_enabled"
                ],

            "supply":
                parsed[
                    "supply"
                ],

            "decimals":
                parsed[
                    "decimals"
                ],

            "security_reasons":
                reasons,

            "security_chain":
                "solana",
        }
