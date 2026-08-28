import os
import base64
import struct
import asyncio

import httpx


class SecurityChecker:
    """
    Solana token security checker.

    Wannan layer ba ya cewa token 100% safe ne.

    Yana duba basic on-chain mint information:

        - token account exists
        - mint authority
        - freeze authority
        - supply
        - decimals
        - initialization

    RPC yana da fallback endpoints domin rage RPC ERROR.
    """

    DEFAULT_RPC = (
        "https://api.mainnet-beta.solana.com"
    )

    FALLBACK_RPCS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
        "https://rpc.ankr.com/solana",
    ]

    MAX_RETRIES = 2

    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 20.0
    WRITE_TIMEOUT = 20.0
    POOL_TIMEOUT = 10.0

    def __init__(self):

        # =====================================
        # CUSTOM RPC
        # =====================================

        custom_rpc = os.getenv(
            "SOLANA_RPC_URL",
            ""
        ).strip()

        # =====================================
        # CUSTOM MULTIPLE RPCS
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
        # BUILD RPC LIST
        # =====================================

        rpc_list = []

        if custom_rpc:
            rpc_list.append(
                custom_rpc
            )

        for rpc in custom_rpcs:
            if rpc not in rpc_list:
                rpc_list.append(rpc)

        for rpc in self.FALLBACK_RPCS:
            if rpc not in rpc_list:
                rpc_list.append(rpc)

        if not rpc_list:
            rpc_list = [
                self.DEFAULT_RPC
            ]

        self.rpc_urls = rpc_list

        # First RPC used initially
        self.rpc_url = self.rpc_urls[0]

        print(
            "🔌 Solana RPC endpoints:",
            len(self.rpc_urls)
        )

    # =========================================
    # RPC REQUEST
    # =========================================

    async def _rpc(
        self,
        method,
        params
    ):
        """
        Send JSON-RPC request.

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

        # =====================================
        # TRY EVERY RPC
        # =====================================

        for rpc_index, rpc_url in enumerate(
            self.rpc_urls,
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
                                f"⚠️ RPC #{rpc_index} "
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

                            # Remember successful RPC
                            self.rpc_url = rpc_url

                            print(
                                f"✅ Solana RPC OK: "
                                f"{rpc_url}"
                            )

                            return data

                        last_error = (
                            "INVALID JSON-RPC RESPONSE"
                        )

                        print(
                            f"⚠️ RPC #{rpc_index} "
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
                        f"⚠️ RPC #{rpc_index} "
                        f"attempt {attempt} "
                        f"TIMEOUT/NETWORK:"
                        f" {rpc_url}"
                    )

                except Exception as exc:

                    last_error = repr(exc)

                    print(
                        f"⚠️ RPC #{rpc_index} "
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
                "Last RPC error:",
                last_error
            )

        return None

    # =========================================
    # GET MINT ACCOUNT
    # =========================================

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

        # =====================================
        # JSON-RPC RESULT
        # =====================================

        result = data.get(
            "result"
        ) or {}

        value = result.get(
            "value"
        )

        if not value:
            return None

        return value

    # =========================================
    # PARSE SPL MINT DATA
    # =========================================

    @staticmethod
    def parse_mint_data(account):
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

    # =========================================
    # SECURITY CHECK
    # =========================================

    async def check(
        self,
        token
    ):
        """
        Run security check for one token.
        """

        chain = str(
            token.get(
                "chain",
                ""
            )
        ).lower()

        address = token.get(
            "address"
        )

        # =====================================
        # ONLY SOLANA
        # =====================================

        if chain != "solana":

            return {
                "security_score": 50,
                "security_status": "UNKNOWN",
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
                    "NON-SOLANA SECURITY "
                    "NOT IMPLEMENTED"
                ],
            }

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

        elif score >= 60:

            status = "🟡 CAUTION"

        else:

            status = "🔴 FAIL"

        # =====================================
        # FINAL SECURITY DECISION
        # =====================================

        should_pass = (
            score >= 90
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
        }
