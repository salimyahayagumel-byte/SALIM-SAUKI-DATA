class FinalSignalEngine:

    # =========================================
    # V10 FINAL SIGNAL THRESHOLDS
    # =========================================

    STRONG_GEM_SCORE = 75
    GEM_SIGNAL_SCORE = 65
    EARLY_GEM_SCORE = 60
    WATCH_SCORE = 50

    # Minimum GEM quality required for signals
    MIN_STRONG_GEM = 72
    MIN_GEM_SIGNAL = 65

    # AI quality
    MIN_AI_SIGNAL = 60

    # Security
    MIN_SECURITY_SCORE = 69

    # Market quality filters
    MIN_LIQUIDITY = 30_000
    MIN_MARKET_CAP = 10_000
    MAX_MARKET_CAP = 1_000_000

    # Buy pressure
    MIN_BUY_RATIO = 0.50

    # Early-entry buy pressure
    EARLY_MIN_BUY_RATIO = 0.50

    # Activity
    MIN_VOLUME_RATIO = 0.03
    MIN_TXNS = 100

    # Abnormal activity protection
    MAX_SAFE_VOLUME_RATIO = 15.0
    EXTREME_VOLUME_RATIO = 25.0

    # =========================================
    # SUPPORTED CHAINS
    # =========================================

    SUPPORTED_CHAINS = {
        "solana",
        "base",
        "robinhood",
        "arc",
    }

    # =========================================
    # EVALUATE
    # =========================================

    @classmethod
    def evaluate(cls, token, security):

        ai_score = cls._number(
            token.get("ai_score")
        )

        gem_score = cls._number(
            token.get("gem_score")
        )

        security_score = cls._number(
            security.get("security_score")
        )

        security_pass = bool(
            security.get(
                "should_pass",
                False
            )
        )

        chain = str(
            token.get(
                "chain",
                ""
            )
        ).lower().strip()

        liquidity = cls._number(
            token.get("liquidity")
        )

        marketcap = cls._number(
            token.get(
                "marketcap",
                token.get(
                    "market_cap"
                )
            )
        )

        buy_ratio = cls._number(
            token.get("buy_ratio")
        )

        volume_ratio = cls._number(
            token.get("volume_ratio")
        )

        total_txns = cls._number(
            token.get("total_txns")
        )

        # Early EVM chains use the looser discovery thresholds. Security
        # remains a hard gate, so lower liquidity does not automatically
        # become a GEM signal.
        if chain in ("base", "robinhood", "arc"):
            # V10.2: EVM chains get a softer final market-activity gate
            # so they can reach the GEM pipeline like Solana. Security
            # and final-signal gates remain authoritative.
            min_liquidity = 3_000
            min_market_cap = 10_000
            min_txns = 10
            min_volume_ratio = 0.02
            signal_buy_ratio = 0.45
            early_buy_ratio = 0.45
        else:
            min_liquidity = cls.MIN_LIQUIDITY
            min_market_cap = cls.MIN_MARKET_CAP
            min_txns = cls.MIN_TXNS
            min_volume_ratio = cls.MIN_VOLUME_RATIO
            signal_buy_ratio = cls.MIN_BUY_RATIO
            early_buy_ratio = cls.EARLY_MIN_BUY_RATIO

        reasons = []

        hard_reject = False

        # =========================================
        # BASIC QUALITY FLAGS
        # =========================================

        gem_quality_ok = (
            gem_score >= cls.MIN_GEM_SIGNAL
        )

        strong_gem_quality = (
            gem_score >= cls.MIN_STRONG_GEM
        )

        ai_quality_ok = (
            ai_score >= cls.MIN_AI_SIGNAL
        )

        buy_pressure_ok = (
            buy_ratio >= signal_buy_ratio
        )

        early_buy_pressure_ok = (
            buy_ratio >= early_buy_ratio
        )

        # V10: security is a hard gate. A high AI/GEM score can never
        # upgrade an incomplete or failed security result into a signal.
        security_quality_ok = (
            security_pass
            and security_score >= cls.MIN_SECURITY_SCORE
        )

        # =========================================
        # CHAIN CHECK
        # =========================================

        if chain not in cls.SUPPORTED_CHAINS:

            hard_reject = True

            reasons.append(
                f"UNSUPPORTED CHAIN: "
                f"{chain.upper() or 'UNKNOWN'}"
            )

        # =========================================
        # SECURITY CHECK
        # =========================================

        if not security_pass:

            hard_reject = True

            reasons.append(
                "SECURITY CHECK FAILED"
            )

        if security_score < cls.MIN_SECURITY_SCORE:

            hard_reject = True

            reasons.append(
                f"SECURITY BELOW "
                f"{cls.MIN_SECURITY_SCORE}"
            )

        # =========================================
        # LIQUIDITY
        # =========================================

        if liquidity < min_liquidity:

            hard_reject = True

            reasons.append(
                f"LIQUIDITY BELOW "
                f"${min_liquidity:,.0f}"
            )

        # =========================================
        # MARKET CAP
        # =========================================

        if marketcap < min_market_cap:

            hard_reject = True

            reasons.append(
                f"MC BELOW "
                f"${min_market_cap:,.0f}"
            )

        elif marketcap > cls.MAX_MARKET_CAP:

            hard_reject = True

            reasons.append(
                f"MC ABOVE "
                f"${cls.MAX_MARKET_CAP:,.0f}"
            )

        # =========================================
        # VOLUME / MC
        # =========================================

        if volume_ratio < min_volume_ratio:

            hard_reject = True

            reasons.append(
                f"VOLUME/MC BELOW "
                f"{min_volume_ratio:.2f}"
            )

        # =========================================
        # TRANSACTIONS
        # =========================================

        if total_txns < min_txns:

            hard_reject = True

            reasons.append(
                f"TXNS BELOW "
                f"{min_txns}"
            )

        # =========================================
        # ABNORMAL VOLUME
        # =========================================

        abnormal_volume = (
            volume_ratio >= cls.MAX_SAFE_VOLUME_RATIO
        )

        extreme_volume = (
            volume_ratio >= cls.EXTREME_VOLUME_RATIO
        )

        if abnormal_volume:

            reasons.append(
                "ABNORMAL VOLUME/MC"
            )

        if extreme_volume:

            reasons.append(
                "EXTREME VOLUME/MC"
            )

        # =========================================
        # SCORE
        # =========================================

        final_score = cls._final_score(
            ai_score,
            gem_score,
            security_score
        )

        # =========================================
        # GEM QUALITY REASONS
        # =========================================

        if gem_score < cls.MIN_STRONG_GEM:

            reasons.append(
                f"GEM BELOW "
                f"{cls.MIN_STRONG_GEM}"
            )

        if ai_score < cls.MIN_AI_SIGNAL:

            reasons.append(
                f"AI BELOW "
                f"{cls.MIN_AI_SIGNAL}"
            )

        # =========================================
        # BUY PRESSURE INFORMATION
        # =========================================

        if (
            buy_ratio < cls.MIN_BUY_RATIO
            and buy_ratio >= cls.EARLY_MIN_BUY_RATIO
        ):

            reasons.append(
                f"BUY PRESSURE "
                f"{buy_ratio:.2%} "
                f"BELOW SIGNAL LEVEL "
                f"{signal_buy_ratio:.2%}"
            )

        elif buy_ratio < early_buy_ratio:

            reasons.append(
                f"BUY PRESSURE BELOW "
                f"{early_buy_ratio:.2%}"
            )

        # =========================================
        # HARD REJECTION
        #
        # IMPORTANT:
        #
        # BUY RATIO BELOW 0.55 IS NOT A HARD
        # REJECT ANYMORE IF IT IS >= 0.50.
        #
        # This allows EARLY GEM / WATCH analysis.
        # =========================================

        if hard_reject:

            return cls._result(
                final_score=final_score,
                should_signal=False,
                status="REJECT",
                signal="⛔ NO SIGNAL",
                reasons=reasons,
                ai_score=ai_score,
                gem_score=gem_score,
                security_score=security_score,
            )

        # =========================================
        # STRONG GEM
        #
        # REQUIRE:
        #
        # GEM >= 75
        # AI >= 65
        # SECURITY PASS
        # EVM BUY >= 0.45 / Solana BUY >= 0.50
        # FINAL >= 80
        #
        # Abnormal volume does not automatically
        # reject, but extreme volume blocks strongest
        # signal.
        # =========================================

        if (
            strong_gem_quality
            and ai_quality_ok
            and security_quality_ok
            and buy_pressure_ok
            and final_score >= cls.STRONG_GEM_SCORE
        ):

            if extreme_volume:

                reasons.append(
                    "STRONG GEM BLOCKED "
                    "BY EXTREME VOLUME"
                )

            else:

                reasons.append(
                    "STRONG GEM CONFIRMED"
                )

                return cls._result(
                    final_score=final_score,
                    should_signal=True,
                    status="STRONG GEM",
                    signal="🔥 STRONG GEM",
                    reasons=reasons,
                    ai_score=ai_score,
                    gem_score=gem_score,
                    security_score=security_score,
                )

        # =========================================
        # GEM SIGNAL
        #
        # REQUIRE:
        #
        # GEM >= 70
        # AI >= 65
        # SECURITY PASS
        # EVM BUY >= 0.45 / Solana BUY >= 0.50
        # FINAL >= 70
        # =========================================

        if (
            gem_quality_ok
            and ai_quality_ok
            and security_quality_ok
            and buy_pressure_ok
            and final_score >= cls.GEM_SIGNAL_SCORE
        ):

            if extreme_volume:

                reasons.append(
                    "GEM SIGNAL BLOCKED "
                    "BY EXTREME VOLUME"
                )

            else:

                reasons.append(
                    "GEM SIGNAL CONFIRMED"
                )

                return cls._result(
                    final_score=final_score,
                    should_signal=True,
                    status="GEM SIGNAL",
                    signal="🚀 GEM SIGNAL",
                    reasons=reasons,
                    ai_score=ai_score,
                    gem_score=gem_score,
                    security_score=security_score,
                )

        # =========================================
        # EARLY GEM
        #
        # REQUIRE:
        #
        # GEM >= 60
        # AI >= 55
        # SECURITY PASS
        # EVM BUY >= 0.45 / Solana BUY >= 0.50
        # FINAL >= 60
        #
        # IMPORTANT:
        #
        # EARLY GEM is eligible for Auto Signal delivery when all
        # other automatic gates pass.
        # =========================================

        if (
            gem_score >= cls.EARLY_GEM_SCORE
            and ai_score >= 55
            and security_quality_ok
            and early_buy_pressure_ok
            and final_score >= cls.EARLY_GEM_SCORE
        ):

            reasons.append(
                "EARLY ENTRY CANDIDATE"
            )

            if buy_ratio < signal_buy_ratio:

                reasons.append(
                    "BUY PRESSURE NOT YET "
                    "STRONG ENOUGH FOR GEM SIGNAL"
                )

            return cls._result(
                final_score=final_score,
                should_signal=True,
                status="EARLY GEM",
                signal="👀 EARLY GEM",
                reasons=reasons,
                ai_score=ai_score,
                gem_score=gem_score,
                security_score=security_score,
            )

        # =========================================
        # WATCH
        # =========================================

        if final_score >= cls.WATCH_SCORE:

            reasons.append(
                "WATCH ONLY"
            )

            return cls._result(
                final_score=final_score,
                should_signal=False,
                status="WATCH",
                signal="🟡 WATCH",
                reasons=reasons,
                ai_score=ai_score,
                gem_score=gem_score,
                security_score=security_score,
            )

        # =========================================
        # NO SIGNAL
        # =========================================

        reasons.append(
            "QUALITY BELOW SIGNAL THRESHOLD"
        )

        return cls._result(
            final_score=final_score,
            should_signal=False,
            status="REJECT",
            signal="⛔ NO SIGNAL",
            reasons=reasons,
            ai_score=ai_score,
            gem_score=gem_score,
            security_score=security_score,
        )

    # =========================================
    # RESULT
    # =========================================

    @staticmethod
    def _result(
        final_score,
        should_signal,
        status,
        signal,
        reasons,
        ai_score,
        gem_score,
        security_score,
    ):

        return {

            "final_score": int(
                final_score
            ),

            "should_signal": bool(
                should_signal
            ),

            "status": status,

            "signal": signal,

            # Both keys intentionally carry the same canonical final
            # decision for backward compatibility.
            "final_signal": signal,
            "signal": signal,
            "signal_source": "final_signal_engine",

            "reasons": reasons,

            # Compatibility aliases
            "final_reasons": reasons,
            "signal_reasons": reasons,

            "ai_score": int(
                ai_score
            ),

            "gem_score": int(
                gem_score
            ),

            "security_score": int(
                security_score
            ),
        }

    # =========================================
    # NUMBER HELPER
    # =========================================

    @staticmethod
    def _number(value):

        try:

            if value is None:

                return 0.0

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

    # =========================================
    # FINAL WEIGHTED SCORE
    # =========================================

    @staticmethod
    def _final_score(
        ai_score,
        gem_score,
        security_score,
    ):

        score = (

            (ai_score * 0.35)

            + (gem_score * 0.40)

            + (security_score * 0.25)

        )

        return max(
            0,
            min(
                int(round(score)),
                100
            )
        )
