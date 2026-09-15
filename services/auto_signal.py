"""
SALIM SAUKI DATA
DEX ANALYSIS BOT
AUTO TELEGRAM SIGNAL ENGINE V7.2 PRO CARD

Features:
    - Automatic Solana token scanning
    - Automatic Base token scanning
    - Multi-chain signal scanning
    - Final signal filtering
    - Recommendation filtering
    - Security filtering
    - Candidate ranking
    - Best-signal-first delivery
    - Duplicate protection
    - Cooldown protection
    - Signal history
    - Telegram delivery
    - DexScreener socials
    - X / Twitter detection
    - Telegram detection
    - Website detection
    - Token tools
    - Chain-aware token tools
    - Clean signal formatting

AUTO SIGNAL POLICY:
    - STRONG GEM -> SEND
    - GEM SIGNAL -> SEND
    - EARLY GEM -> MONITOR ONLY
    - WATCH -> MONITOR ONLY
    - NO SIGNAL -> IGNORE

NOT FINANCIAL ADVICE.
"""

import asyncio
import time
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import quote

from config import (
    DATABASE_URL,
    PNL_TRACKER_ENABLED,
    PNL_TRACKER_INTERVAL,
    PNL_TRACKER_MAX_TRACKED,
    PNL_TRACKER_DRAWDOWN_ALERT,
)
from services.scanner import TokenScanner
from services.history import SignalHistory
from services.pnl_tracker import PNLTracker


class AutoSignalEngine:

    # =========================================================
    # PRO CARD VERSION
    # =========================================================

    FORMAT_VERSION = "V8.7-INTELLIGENCE"

    # =========================================================
    # DEFAULT SETTINGS
    # =========================================================

    DEFAULT_INTERVAL = 60

    DEFAULT_COOLDOWN = 3600

    DEFAULT_MAX_SIGNALS_PER_SCAN = 3

    # Keep multi-chain delivery fair. A chain may contribute up to
    # this many signals before the remaining global slots are filled
    # by the best remaining candidates.
    DEFAULT_MAX_SIGNALS_PER_CHAIN = 2

    MIN_RECOMMENDATION_SCORE = 65

    MIN_FINAL_SCORE = 65

    MIN_SECURITY_SCORE = 70

    MAX_HISTORY = 5000

    # =========================================================
    # SUPPORTED CHAINS
    # =========================================================

    SUPPORTED_CHAINS = (
        "solana",
        "base",
    )

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
        max_signals_per_chain: int = DEFAULT_MAX_SIGNALS_PER_CHAIN,
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

        self.max_signals_per_chain = max(
            1,
            int(
                max_signals_per_chain
                or self.DEFAULT_MAX_SIGNALS_PER_CHAIN
            ),
        )

        # Chain + contract keys are used everywhere for duplicate and
        # cooldown protection. This prevents a Solana address and a Base
        # address with the same textual value from colliding.
        self.scanner = TokenScanner()

        # =====================================================
        # SENT CONTRACTS
        # =====================================================

        self.sent_contracts: Set[str] = set()

        # =====================================================
        # SIGNAL HISTORY
        # =====================================================

        self.signal_history: Dict[str, float] = {}

        # Persistent history survives Telegram/process restarts.
        self.history_store = SignalHistory(DATABASE_URL)

        # PNL tracker follows only successfully delivered signals.
        self.pnl_tracker = PNLTracker(
            bot=self.bot,
            chat_id=self.chat_id,
            database_url=DATABASE_URL,
            interval=max(15, PNL_TRACKER_INTERVAL or self.interval),
            max_tracked=max(50, PNL_TRACKER_MAX_TRACKED),
            enabled=PNL_TRACKER_ENABLED,
            drawdown_alert=max(1.0, PNL_TRACKER_DRAWDOWN_ALERT),
        )
        self.signal_history.update(
            self.history_store.load_recent(self.cooldown)
        )
        self.sent_contracts.update(
            self.signal_history.keys()
        )

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

        self.scan_failures = 0
        self.last_scan_at = 0.0
        self.last_scan_summary: Dict[str, Any] = {}

        # Rejection diagnostics make it clear why a scan produced
        # no signal instead of silently filtering every candidate.
        self.rejection_stats: Dict[str, int] = {}

        # =====================================================
        # SOCIAL ENRICHMENT CACHE
        # =====================================================

        self.social_cache: Dict[
            str,
            Dict[str, Any]
        ] = {}

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

        await self.pnl_tracker.start()

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
            f"⚖️ Max signals/chain: "
            f"{self.max_signals_per_chain}"
        )

        print(
            "🟣 Solana scanner: ENABLED"
        )

        print(
            "🔵 Base scanner: ENABLED"
        )

        print(
            "🌐 DexScreener socials: ENABLED"
        )

        print(
            "🧭 V8.7 diagnostics: ENABLED"
        )

        print(
            "🚀 AUTO SIGNAL ENGINE V5 STARTED"
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

        try:
            self.pnl_tracker.stop()
        except Exception as exc:
            print(f"⚠️ PNL tracker stop error: {exc}")

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

        print(
            f"❌ Telegram errors: "
            f"{self.telegram_errors}"
        )

    # =========================================================
    # SCAN ONE CHAIN
    # =========================================================

    async def _scan_chain(
        self,
        chain: str,
    ) -> List[Dict[str, Any]]:

        chain = str(
            chain or ""
        ).lower().strip()

        if chain not in self.SUPPORTED_CHAINS:

            print(
                f"⚠️ Unsupported auto-signal chain: "
                f"{chain}"
            )

            return []

        try:

            results = await self.scanner.scan(
                chain
            )

        except Exception as exc:

            print(
                f"❌ {chain.upper()} scanner error: "
                f"{exc}"
            )

            return []

        if not results:

            print(
                f"📊 {chain.upper()} candidates: 0"
            )

            return []

        print(
            f"📊 {chain.upper()} candidates: "
            f"{len(results)}"
        )

        return [
            token
            for token in results
            if isinstance(
                token,
                dict,
            )
        ]

    # =========================================================
    # SCAN ONCE
    # =========================================================

    async def scan_once(self):

        self.scan_count += 1
        self.rejection_stats = {}
        self.last_scan_at = time.time()

        print("")

        print(
            "🔎 Auto Signal: scanning..."
        )

        # =====================================================
        # MULTI-CHAIN SCAN
        # =====================================================

        solana_results = await self._scan_chain(
            "solana"
        )

        base_results = await self._scan_chain(
            "base"
        )

        results: List[
            Dict[str, Any]
        ] = []

        results.extend(
            solana_results
        )

        results.extend(
            base_results
        )

        print(
            f"📊 Total candidates found: "
            f"{len(results)}"
        )

        for chain_name, chain_results in (
            ("solana", solana_results),
            ("base", base_results),
        ):
            stats = getattr(
                self.scanner,
                "last_scan_stats",
                {},
            )
            # The scanner is shared, so chain-level stats are most
            # useful immediately after each chain scan. The detailed
            # pipeline is already printed by TokenScanner; here we keep
            # the aggregate count explicit for the auto engine.
            print(
                f"🧭 AUTO {chain_name.upper()} result count: "
                f"{len(chain_results)}"
            )

        self.last_scan_summary = {
            "scan": self.scan_count,
            "solana_candidates": len(solana_results),
            "base_candidates": len(base_results),
            "total_candidates": len(results),
            "rejections": dict(self.rejection_stats),
            "signals_sent_total": self.signals_sent,
            "telegram_errors_total": self.telegram_errors,
        }

        if not results:

            print(
                "📊 Candidates found: 0"
            )

            return

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

            rejection_reason = self._signal_rejection_reason(
                token
            )

            if rejection_reason:

                self._record_rejection(
                    rejection_reason
                )

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
            # CHAIN
            # -------------------------------------------------

            chain = str(
                token.get(
                    "chain",
                    "",
                )
                or ""
            ).lower().strip()

            if chain not in self.SUPPORTED_CHAINS:

                self.filtered_out += 1

                continue

            # -------------------------------------------------
            # CHAIN + CONTRACT KEY
            # -------------------------------------------------

            signal_key = self._signal_key(
                token
            )

            # -------------------------------------------------
            # CURRENT SCAN DUPLICATE
            # -------------------------------------------------

            if signal_key in current_scan:

                self.duplicates_skipped += 1

                continue

            current_scan.add(
                signal_key
            )

            # -------------------------------------------------
            # COOLDOWN
            # -------------------------------------------------

            if self._is_on_cooldown(
                signal_key
            ):

                self.cooldown_skipped += 1

                print(
                    f"⏳ Cooldown active: "
                    f"${token.get('symbol', 'N/A')} "
                    f"[{chain.upper()}]"
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

            self._print_rejection_summary()

            self.last_scan_summary.update({
                "ranked_candidates": 0,
                "selected_candidates": 0,
                "signals_sent_this_scan": 0,
            })

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
        # FAIR MULTI-CHAIN SELECTION
        # =====================================================

        selected_candidates, chain_counts = self._select_candidates(
            candidates
        )

        self.last_scan_summary.update({
            "ranked_candidates": len(candidates),
            "selected_candidates": len(selected_candidates),
        })

        print(
            "⚖️ Selected signal distribution: "
            + " | ".join(
                f"{chain.upper()}={count}"
                for chain, count in sorted(chain_counts.items())
            )
            if chain_counts
            else "⚖️ Selected signal distribution: none"
        )
        # =====================================================
        # SEND BEST SIGNALS FIRST
        # =====================================================

        sent_this_scan = 0

        for ranking, token in selected_candidates:

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

            chain = str(
                token.get(
                    "chain",
                    "",
                )
                or ""
            ).lower().strip()

            print(
                "🏆 Candidate:",
                f"${symbol}",
                f"[{chain.upper()}]",
                f"REC={self._int(token.get('recommendation_score'))}",
                f"FINAL={self._int(token.get('final_score'))}",
                f"GEM={self._int(token.get('gem_score'))}",
                f"AI={self._int(token.get('ai_score'))}",
                f"SEC={self._int(token.get('security_score'))}",
            )

            # -------------------------------------------------
            # DEXSCREENER SOCIAL ENRICHMENT
            # -------------------------------------------------

            try:

                await self._enrich_socials(
                    token
                )

            except Exception as exc:

                print(
                    f"⚠️ Social enrichment failed "
                    f"for ${symbol}: {exc}"
                )

            # -------------------------------------------------
            # FORMAT
            # -------------------------------------------------

            message = self.format_signal(
                token
            )

            try:

                image_url = str(
                    token.get(
                        "image_url",
                        "",
                    )
                    or ""
                ).strip()

                # -------------------------------------------------
                # TOKEN IMAGE + SIGNAL
                # -------------------------------------------------
                # Send the token artwork above the signal when a
                # valid DexScreener image URL is available.
                # If Telegram cannot fetch the image, fall back
                # to the normal text message so the signal is not lost.
                if image_url.startswith(
                    ("http://", "https://")
                ):

                    try:

                        await self.bot.send_photo(
                            chat_id=self.chat_id,
                            photo=image_url,
                            caption=message,
                            parse_mode="HTML",
                        )

                    except Exception as image_exc:

                        print(
                            f"⚠️ Token image send failed "
                            f"for ${symbol}: {image_exc}"
                        )

                        await self.bot.send_message(
                            chat_id=self.chat_id,
                            text=message,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )

                else:

                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode="HTML",
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

            signal_key = self._signal_key(
                token
            )

            self.sent_contracts.add(
                signal_key
            )

            self.signal_history[
                signal_key
            ] = now

            self.history_store.record(
                signal_key=signal_key,
                chain=chain,
                address=address,
                symbol=symbol,
                score=self._number(token.get("recommendation_score")),
                sent_at=now,
            )

            self.signals_sent += 1

            # Start price-based PNL tracking only after Telegram delivery
            # succeeds, so failed signals never create fake entries.
            try:
                self.pnl_tracker.add_signal(token)
            except Exception as exc:
                print(f"⚠️ PNL tracking setup failed for ${symbol}: {exc}")

            sent_this_scan += 1

            print(
                f"🚀 SIGNAL SENT: "
                f"${symbol} "
                f"[{chain.upper()}] "
                f"{address}"
            )

        # =====================================================
        # HISTORY LIMIT
        # =====================================================

        self._limit_history()

        self._print_rejection_summary()

        self.last_scan_summary["signals_sent_this_scan"] = sent_this_scan

        print(
            f"📤 Signals sent this scan: "
            f"{sent_this_scan}"
        )

    # =========================================================
    # FAIR CANDIDATE SELECTION
    # =========================================================

    def _select_candidates(
        self,
        candidates: List[Tuple[Tuple, Dict[str, Any]]],
    ) -> Tuple[List[Tuple[Tuple, Dict[str, Any]]], Dict[str, int]]:
        """Select a globally limited but multi-chain-fair signal set."""

        selected: List[Tuple[Tuple, Dict[str, Any]]] = []
        selected_keys: Set[str] = set()
        chain_counts: Dict[str, int] = {}

        # Pass 1: give every chain a chance, respecting the per-chain cap.
        for ranking, token in candidates:
            if len(selected) >= self.max_signals_per_scan:
                break

            chain = str(token.get("chain", "") or "").lower().strip()
            signal_key = self._signal_key(token)
            if not signal_key or signal_key in selected_keys:
                continue

            count = chain_counts.get(chain, 0)
            if count >= self.max_signals_per_chain:
                continue

            selected.append((ranking, token))
            selected_keys.add(signal_key)
            chain_counts[chain] = count + 1

        # Pass 2: fill unused global slots with the best remaining signals.
        if len(selected) < self.max_signals_per_scan:
            for ranking, token in candidates:
                if len(selected) >= self.max_signals_per_scan:
                    break

                signal_key = self._signal_key(token)
                if not signal_key or signal_key in selected_keys:
                    continue

                selected.append((ranking, token))
                selected_keys.add(signal_key)
                chain = str(token.get("chain", "") or "").lower().strip()
                chain_counts[chain] = chain_counts.get(chain, 0) + 1

        return selected, chain_counts

    # =========================================================
    # SIGNAL KEY
    # =========================================================

    @staticmethod
    def _signal_key(
        token_or_address: Any,
    ) -> str:

        if isinstance(
            token_or_address,
            dict,
        ):

            chain = str(
                token_or_address.get(
                    "chain",
                    "",
                )
                or ""
            ).lower().strip()

            address = str(
                token_or_address.get(
                    "address",
                    "",
                )
                or ""
            ).strip()

            if chain and address:

                return (
                    f"{chain}:{address}"
                )

            return address

        return str(
            token_or_address or ""
        ).strip()

    # =========================================================
    # DEXSCREENER SOCIAL ENRICHMENT
    # =========================================================

    async def _enrich_socials(
        self,
        token: Dict[str, Any],
    ) -> Dict[str, Any]:

        address = str(
            token.get(
                "address",
                "",
            )
            or ""
        ).strip()

        if not address:

            return token

        chain = str(
            token.get(
                "chain",
                "",
            )
            or ""
        ).lower().strip()

        cache_key = self._signal_key(
            token
        )

        # -----------------------------------------------------
        # Already available?
        # -----------------------------------------------------

        existing_info = token.get(
            "info"
        )

        if isinstance(
            existing_info,
            dict,
        ):

            self._extract_socials(
                token,
                existing_info,
            )

            return token

        # -----------------------------------------------------
        # CACHE
        # -----------------------------------------------------

        cached = self.social_cache.get(
            cache_key
        )

        if isinstance(
            cached,
            dict,
        ):

            self._extract_socials(
                token,
                cached,
            )

            return token

        # -----------------------------------------------------
        # FETCH REAL PAIR DATA
        # -----------------------------------------------------

        try:

            pairs = await self.scanner.dex.tokens(
                [address]
            )

        except Exception as exc:

            print(
                f"⚠️ DexScreener social lookup "
                f"failed for {address}: {exc}"
            )

            return token

        if not pairs:

            return token

        # -----------------------------------------------------
        # Find best pair for requested chain
        # -----------------------------------------------------

        selected_pair = None

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

            if chain and pair_chain != chain:

                continue

            selected_pair = pair

            break

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        if not selected_pair:

            for pair in pairs:

                if not isinstance(
                    pair,
                    dict,
                ):

                    continue

                selected_pair = pair

                break

        if not selected_pair:

            return token

        info = selected_pair.get(
            "info"
        )

        if not isinstance(
            info,
            dict,
        ):

            return token

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        token["info"] = info

        # -----------------------------------------------------
        # TOKEN IMAGE
        # -----------------------------------------------------
        # DexScreener may provide token artwork through info.imageUrl.
        # Keep only a normal HTTP/HTTPS URL. Never treat image URLs
        # as social links.
        image_url = str(
            info.get(
                "imageUrl",
                "",
            )
            or ""
        ).strip()

        if image_url.startswith(
            ("http://", "https://")
        ):

            token["image_url"] = image_url

        else:

            token["image_url"] = ""

        self.social_cache[
            cache_key
        ] = info

        self._extract_socials(
            token,
            info,
        )

        return token

    # =========================================================
    # EXTRACT SOCIALS
    # =========================================================

    @classmethod
    def _extract_socials(
        cls,
        token: Dict[str, Any],
        info: Dict[str, Any],
    ):

        if not isinstance(
            info,
            dict,
        ):

            return

        websites = []

        socials = []

        # =====================================================
        # WEBSITES
        # =====================================================

        raw_websites = info.get(
            "websites",
            [],
        )

        if isinstance(
            raw_websites,
            list,
        ):

            for item in raw_websites:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                url = str(
                    item.get(
                        "url",
                        "",
                    )
                    or ""
                ).strip()

                label = str(
                    item.get(
                        "label",
                        "Website",
                    )
                    or "Website"
                ).strip()

                if not url:

                    continue

                if not cls._valid_social_url(
                    url
                ):

                    continue

                websites.append(
                    {
                        "url": url,
                        "label": label,
                    }
                )

        # =====================================================
        # SOCIALS
        # =====================================================

        raw_socials = info.get(
            "socials",
            [],
        )

        if isinstance(
            raw_socials,
            list,
        ):

            for item in raw_socials:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                url = str(
                    item.get(
                        "url",
                        "",
                    )
                    or ""
                ).strip()

                social_type = str(
                    item.get(
                        "type",
                        "",
                    )
                    or ""
                ).lower().strip()

                if not url:

                    continue

                if not cls._valid_social_url(
                    url
                ):

                    continue

                socials.append(
                    {
                        "url": url,
                        "type": social_type,
                    }
                )

        token["websites"] = websites

        token["socials"] = socials

        token["twitter_url"] = cls._find_social(
            socials,
            (
                "twitter",
                "x",
            ),
        )

        token["telegram_url"] = cls._find_social(
            socials,
            (
                "telegram",
                "tg",
            ),
        )

        token["discord_url"] = cls._find_social(
            socials,
            (
                "discord",
            ),
        )

        token["website_url"] = (
            websites[0]["url"]
            if websites
            else ""
        )

    # =========================================================
    # FIND SOCIAL
    # =========================================================

    @staticmethod
    def _find_social(
        socials: List[Dict[str, Any]],
        types: Tuple[str, ...],
    ) -> str:

        for item in socials:

            social_type = str(
                item.get(
                    "type",
                    "",
                )
                or ""
            ).lower().strip()

            url = str(
                item.get(
                    "url",
                    "",
                )
                or ""
            ).strip()

            if not url:

                continue

            if social_type in types:

                return url

            # Extra protection for X/Twitter
            if (
                "twitter.com/" in url.lower()
                or "x.com/" in url.lower()
            ):

                if (
                    "twitter" in types
                    or "x" in types
                ):

                    return url

            # Extra protection for Telegram
            if "t.me/" in url.lower():

                if (
                    "telegram" in types
                    or "tg" in types
                ):

                    return url

        return ""

    # =========================================================
    # URL VALIDATION
    # =========================================================

    @staticmethod
    def _valid_social_url(
        url: str,
    ) -> bool:

        value = str(
            url or ""
        ).strip()

        if not value:

            return False

        # Never allow image URLs into socials.
        blocked = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            "/cms/images/",
            "/token-images/",
        )

        lower = value.lower()

        if any(
            item in lower
            for item in blocked
        ):

            return False

        if not (
            lower.startswith("http://")
            or lower.startswith("https://")
        ):
            return False

        # Reject obvious generic X/Twitter status links. DexScreener
        # occasionally surfaces unrelated posts (for example a post by
        # a famous account) as social metadata. Auto signals should link
        # to a project profile, not an arbitrary status.
        if "x.com/" in lower or "twitter.com/" in lower:
            path = lower.split("//", 1)[-1].split("/", 1)
            path = path[1] if len(path) > 1 else ""
            parts = [p for p in path.split("/") if p]
            if not parts:
                return False
            if parts[0] in {"status", "i", "intent", "share"}:
                return False
            if len(parts) >= 2 and parts[1] == "status":
                return False

        # Reject Telegram invite/hash-only URLs that cannot be presented
        # reliably as a public project channel/group link.
        if "t.me/" in lower:
            host_part = lower.split("t.me/", 1)[-1].split("?", 1)[0].strip("/")
            if not host_part or host_part.startswith("+"):
                return False

        return True

    # =========================================================
    # SIGNAL FILTER
    # =========================================================

    @classmethod
    def _signal_rejection_reason(
        cls,
        token: Dict[str, Any],
    ) -> str:
        """Return the exact auto-signal gate that rejected a token."""
        if not isinstance(token, dict):
            return "invalid_token"

        if not token.get("final_should_signal", False):
            return "final_signal"

        if not token.get("is_recommended", False):
            return "recommendation"

        if not token.get("security_should_pass", False):
            return "security_gate"

        security_score = cls._number(
            token.get("security_score", 0)
        )
        if security_score < cls.MIN_SECURITY_SCORE:
            return "security_score"

        recommendation_score = cls._number(
            token.get("recommendation_score", 0)
        )
        if recommendation_score < cls.MIN_RECOMMENDATION_SCORE:
            return "recommendation_score"

        final_score = cls._number(
            token.get("final_score", 0)
        )
        if final_score < cls.MIN_FINAL_SCORE:
            return "final_score"

        return ""

    @classmethod
    def _is_signal(
        cls,
        token: Dict[str, Any],
    ) -> bool:
        return cls._signal_rejection_reason(token) == ""

    def _record_rejection(self, reason: str):
        if not reason:
            return
        self.rejection_stats[reason] = (
            self.rejection_stats.get(reason, 0) + 1
        )

    def _print_rejection_summary(self):
        if not self.rejection_stats:
            print("🧪 Auto Signal gates: no rejected candidates recorded.")
            return

        ordered = sorted(
            self.rejection_stats.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        summary = " | ".join(
            f"{reason}={count}"
            for reason, count in ordered
        )

        print(
            "🧪 Auto Signal rejection summary: "
            + summary
        )

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

        # Base/Solana chain tie-breaker is added last.
        chain = str(
            token.get(
                "chain",
                "",
            )
            or ""
        ).lower().strip()

        chain_priority = (
            1
            if chain == "base"
            else 0
        )

        return (
            recommendation_score,
            final_score,
            gem_score,
            ai_score,
            security_score,
            buy_ratio,
            liquidity_ratio,
            volume_ratio,
            chain_priority,
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

        self.history_store.prune(
            self.MAX_HISTORY
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
        """Build the professional Telegram GEM signal card.

        Only data already present in the scanner token is displayed.
        Optional fields such as ATH, holders, and developer metrics are
        shown only when real values are supplied by the scanner.
        """

        symbol = cls._escape_html(str(token.get("symbol", "N/A") or "N/A"))
        name = cls._escape_html(str(token.get("name", "Unknown") or "Unknown"))

        chain = str(token.get("chain", "solana") or "solana").lower().strip()
        chain_name = (
            "🔵 Base" if chain == "base" else "🟣 Solana"
        )

        final_signal = str(
            token.get("final_signal", token.get("signal", "⛔ NO SIGNAL"))
            or "⛔ NO SIGNAL"
        ).upper()

        if "STRONG GEM" in final_signal:
            signal_icon = "🔥"
            signal_label = "STRONG GEM"
        elif "GEM SIGNAL" in final_signal:
            signal_icon = "🚀"
            signal_label = "GEM SIGNAL"
        elif "EARLY GEM" in final_signal:
            signal_icon = "👀"
            signal_label = "EARLY GEM"
        elif "WATCH" in final_signal:
            signal_icon = "🟡"
            signal_label = "WATCH"
        else:
            signal_icon = "⛔"
            signal_label = final_signal.replace("⛔ ", "") or "NO SIGNAL"

        final_score = cls._int(token.get("final_score", 0))
        ai_score = cls._int(token.get("ai_score", 0))
        gem_score = cls._int(token.get("gem_score", 0))
        security_score = cls._int(token.get("security_score", 0))
        recommendation_score = cls._int(token.get("recommendation_score", 0))
        confidence = cls._int(token.get("recommendation_confidence", token.get("confidence", 0)))
        buy_ratio = cls._number(token.get("buy_ratio", 0))
        total_txns = cls._int(token.get("total_txns", 0))
        price_change = cls._number(token.get("price_change_24h", 0))
        marketcap = cls._number(token.get("marketcap", 0))
        liquidity = cls._number(token.get("liquidity", 0))
        volume = cls._number(token.get("volume24h", 0))
        address = str(token.get("address", "") or "").strip()

        recommendation = cls._escape_html(
            str(token.get("recommendation", "") or "").strip()
        )
        risk = cls._escape_html(
            str(token.get("recommendation_risk", token.get("risk_level", "")) or "").strip()
        )
        security_confidence = cls._escape_html(
            str(token.get("security_confidence", "") or "").strip()
        )

        # -----------------------------------------------------
        # AGE — calculated only when pair_created is real data.
        # -----------------------------------------------------
        age_text = ""
        pair_created = token.get("pair_created")
        try:
            created_ms = float(pair_created or 0)
            if created_ms > 0:
                age_seconds = max(0, int(time.time() - (created_ms / 1000)))
                if age_seconds < 3600:
                    age_text = f"{age_seconds // 60}m"
                elif age_seconds < 86400:
                    age_text = f"{age_seconds // 3600}h"
                else:
                    age_text = f"{age_seconds // 86400}d"
        except (TypeError, ValueError, OverflowError):
            age_text = ""

        # -----------------------------------------------------
        # SOCIALS
        # -----------------------------------------------------
        twitter_url = str(token.get("twitter_url", "") or "").strip()
        telegram_url = str(token.get("telegram_url", "") or "").strip()
        website_url = str(token.get("website_url", "") or "").strip()

        # -----------------------------------------------------
        # CHAIN TOOLS
        # -----------------------------------------------------
        encoded_address = quote(address, safe="") if address else ""
        dex_url = str(token.get("url", "") or "").strip()

        if chain == "base":
            scan_url = f"https://basescan.org/token/{encoded_address}" if encoded_address else ""
            scan_label = "BaseScan"
            gecko_url = f"https://www.geckoterminal.com/base/tokens/{encoded_address}" if encoded_address else ""
            gmgn_url = f"https://gmgn.ai/base/token/{encoded_address}" if encoded_address else ""
        else:
            scan_url = f"https://solscan.io/token/{encoded_address}" if encoded_address else ""
            scan_label = "Solscan"
            gecko_url = f"https://www.geckoterminal.com/solana/tokens/{encoded_address}" if encoded_address else ""
            gmgn_url = f"https://gmgn.ai/sol/token/{encoded_address}" if encoded_address else ""

        # -----------------------------------------------------
        # CARD HEADER
        # -----------------------------------------------------
        lines = [
            "🔥 <b>SALIM SAUKI DATA — GEM SIGNAL</b>",
            f"{signal_icon} <b>${symbol}</b> — {name}",
            f"{chain_name} • <b>{signal_label}</b>",
        ]

        price = cls._number(token.get("price", token.get("price_usd", 0)))
        if price > 0:
            lines.append(f"💵 Price: <b>{cls._format_price(price)}</b>")

        if age_text:
            lines.append(f"🕒 Age: <b>{age_text}</b>")

        lines.extend([
            "🛡 Security: <b>⚠️ REVIEW</b>" if security_score < 80 else "🛡 Security: <b>✅ PASS</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

        if dex_url:
            lines.append(f'🔗 <a href="{cls._escape_attribute(dex_url)}">Chart</a>')

        lines.append("━━━━━━━━━━━━━━━━━━━━")

        # -----------------------------------------------------
        # MARKET
        # -----------------------------------------------------
        lines.extend([
            "",
            "💰 <b>MARKET</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"┗ MC: <b>${marketcap:,.0f}</b>",
        ])

        ath = token.get("ath") or token.get("ath_marketcap") or token.get("ath_mc")
        ath_value = cls._number(ath, 0)
        if ath_value > 0:
            lines.append(f"┗ ATH: <b>${ath_value:,.0f}</b>")

        lines.append(f"┗ Liquidity: <b>${liquidity:,.0f}</b>")

        # -----------------------------------------------------
        # VOLUME / TRADING
        # -----------------------------------------------------
        lines.extend([
            "",
            "📈 <b>VOLUME</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"┗ 24h: <b>${volume:,.0f}</b>",
            f"┗ Transactions: <b>{total_txns:,}</b>",
            "",
            "📊 <b>TRADING</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🟢 Buys: <b>{buy_ratio * 100:.1f}%</b>",
            f"🔴 Sells: <b>{max(0.0, (1 - buy_ratio) * 100):.1f}%</b>",
        ])

        if price_change != 0:
            lines.append(f"📉 24h Change: <b>{price_change:+.2f}%</b>")

        # -----------------------------------------------------
        # SCORES
        # -----------------------------------------------------
        lines.extend([
            "",
            "🤖 <b>ANALYSIS</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"┗ AI Score: <b>{ai_score}/100</b>",
            f"┗ GEM Score: <b>{gem_score}/100</b>",
            f"┗ Security Score: <b>{security_score}/100</b>",
            f"┗ Final Score: <b>{final_score}/100</b>",
        ])

        if recommendation:
            lines.append(f"🎯 Recommendation: <b>{recommendation}</b>")
        if recommendation_score:
            lines.append(f"┗ Score: <b>{recommendation_score}/100</b>")
        if confidence:
            lines.append(f"┗ Confidence: <b>{confidence}%</b>")
        if risk:
            lines.append(f"┗ Risk: <b>{risk}</b>")
        if security_confidence:
            lines.append(f"┗ Evidence: <b>{security_confidence}</b>")

        # -----------------------------------------------------
        # OPTIONAL REAL DATA — never fabricate missing fields.
        # -----------------------------------------------------
        holders = token.get("holders") or token.get("holder_count")
        holder_count = cls._int(holders, 0)
        if holder_count > 0:
            lines.extend(["", "👥 <b>Holders</b>", f"┗ Holders: <b>{holder_count:,}</b>"])

        dev_balance = token.get("dev_balance")
        sold = token.get("dev_sold") or token.get("sold_percent")
        airdrops = token.get("airdrops") or token.get("airdrop_percent")
        burnt = token.get("burnt") or token.get("burned_percent")
        dev_items = []
        if dev_balance not in (None, ""):
            dev_items.append(f"┗ Dev balance: <b>{cls._escape_html(str(dev_balance))}</b>")
        if sold not in (None, ""):
            dev_items.append(f"┗ Sold: <b>{cls._number(sold):.1f}%</b>")
        if airdrops not in (None, ""):
            dev_items.append(f"┗ Airdrops: <b>{cls._number(airdrops):.1f}%</b>")
        if burnt not in (None, ""):
            dev_items.append(f"┗ Burnt: <b>{cls._number(burnt):.1f}%</b>")
        if dev_items:
            lines.extend(["", "👨‍💻 <b>Dev</b>", *dev_items])

        # -----------------------------------------------------
        # SOCIALS
        # -----------------------------------------------------
        social_lines = []
        if twitter_url:
            social_lines.append(f'<a href="{cls._escape_attribute(twitter_url)}">𝕏 X</a>')
        if telegram_url:
            social_lines.append(f'<a href="{cls._escape_attribute(telegram_url)}">Telegram</a>')
        if website_url:
            social_lines.append(f'<a href="{cls._escape_attribute(website_url)}">Website</a>')
        if social_lines:
            lines.extend(["", "🔗 <b>SOCIALS</b>", "━━━━━━━━━━━━━━━━━━━━", "┗ " + " • ".join(social_lines)])

        tool_lines = []
        if scan_url:
            tool_lines.append(f'<a href="{cls._escape_attribute(scan_url)}">{scan_label}</a>')
        if gecko_url:
            tool_lines.append(f'<a href="{cls._escape_attribute(gecko_url)}">GeckoTerminal</a>')
        if gmgn_url:
            tool_lines.append(f'<a href="{cls._escape_attribute(gmgn_url)}">GMGN</a>')
        if tool_lines:
            lines.extend(["", "🔎 <b>TOOLS</b>", "━━━━━━━━━━━━━━━━━━━━", "┗ " + " • ".join(tool_lines)])

        if address:
            lines.extend([
                "",
                f"📄 <code>{cls._escape_html(address)}</code>",
            ])

        lines.extend([
            "",
            "⚠️ <i>DYOR — Early GEM signal, not financial advice.</i>",
        ])

        message = "\n".join(lines)

        # Telegram photo captions have a 1024-character limit.
        # Keep the full professional card when possible and fall back
        # to a compact but still readable card if optional data grows it.
        if len(message) > 1000:
            essential = [
                "🔥 <b>SALIM SAUKI DATA — GEM SIGNAL</b>",
                f"{signal_icon} <b>${symbol}</b> — {name}",
                f"{chain_name} • <b>{signal_label}</b>",
                "",
                f"💰 MC: <b>${marketcap:,.0f}</b>",
                f"💧 Liquidity: <b>${liquidity:,.0f}</b>",
                f"📈 24h Volume: <b>${volume:,.0f}</b>",
                f"📊 TXNS: <b>{total_txns:,}</b>",
                f"🟢 Buys: <b>{buy_ratio * 100:.1f}%</b>",
                "",
                f"🤖 AI: <b>{ai_score}/100</b>",
                f"💎 GEM: <b>{gem_score}/100</b>",
                f"🛡 Security: <b>{security_score}/100</b>",
                f"🎯 Final: <b>{final_score}/100</b>",
            ]
            if scan_url:
                essential.append(f'🔗 <a href="{cls._escape_attribute(scan_url)}">{scan_label}</a>')
            if dex_url:
                essential.append(f'🔗 <a href="{cls._escape_attribute(dex_url)}">Chart</a>')
            if address:
                essential.append(f"📄 <code>{cls._escape_html(address)}</code>")
            essential.extend(["", "⚠️ <i>DYOR — Not financial advice.</i>"])
            message = "\n".join(essential)

        return message
    # =========================================================
    # PRICE FORMAT
    # =========================================================

    @staticmethod
    def _format_price(value: Any) -> str:

        try:
            price = float(value or 0)
        except (TypeError, ValueError):
            return "$0"

        if price <= 0:
            return "$0"
        if price >= 1:
            return f"${price:,.6f}".rstrip("0").rstrip(".")
        if price >= 0.01:
            return f"${price:.8f}".rstrip("0").rstrip(".")
        return f"${price:.12f}".rstrip("0").rstrip(".")

    # =========================================================
    # HTML ESCAPE
    # =========================================================

    @staticmethod
    def _escape_html(
        value: str,
    ) -> str:

        value = str(
            value or ""
        )

        return (
            value
            .replace(
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

    # =========================================================
    # HTML ATTRIBUTE ESCAPE
    # =========================================================

    @staticmethod
    def _escape_attribute(
        value: str,
    ) -> str:

        value = str(
            value or ""
        )

        return (
            value
            .replace(
                "&",
                "&amp;",
            )
            .replace(
                '"',
                "&quot;",
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


# =============================================================
# SIMPLE TEST
# =============================================================

async def test_engine():

    class FakeBot:

        async def send_message(
            self,
            chat_id,
            text,
            parse_mode="HTML",
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
