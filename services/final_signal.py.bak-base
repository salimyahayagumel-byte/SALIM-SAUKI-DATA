class FinalSignalEngine:

    # =========================================
    # V5 SIGNAL THRESHOLDS
    # =========================================

    STRONG_GEM_SCORE = 80
    GEM_SIGNAL_SCORE = 70
    EARLY_GEM_SCORE = 60
    WATCH_SCORE = 50

    # Minimum GEM quality required for signals
    MIN_STRONG_GEM = 75
    MIN_GEM_SIGNAL = 70

    # AI quality
    MIN_AI_SIGNAL = 65

    # Security
    MIN_SECURITY_SCORE = 80

    # Market quality filters
    MIN_LIQUIDITY = 20_000
    MIN_MARKET_CAP = 30_000
    MAX_MARKET_CAP = 5_000_000

    # Buy pressure
    MIN_BUY_RATIO = 0.55

    # Activity
    MIN_VOLUME_RATIO = 0.05
    MIN_TXNS = 50

    # Abnormal activity protection
    MAX_SAFE_VOLUME_RATIO = 15.0
    EXTREME_VOLUME_RATIO = 25.0

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
        ).lower()

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
            buy_ratio >= cls.MIN_BUY_RATIO
        )

        security_quality_ok = (
            security_pass
            and security_score >= cls.MIN_SECURITY_SCORE
        )

        # =========================================
        # CHAIN CHECK
        # =========================================

        if chain != "solana":

            hard_reject = True

            reasons.append(
                "NOT SOLANA"
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

        if liquidity < cls.MIN_LIQUIDITY:

            hard_reject = True

            reasons.append(
                f"LIQUIDITY BELOW "
                f"${cls.MIN_LIQUIDITY:,.0f}"
            )

        # =========================================
        # MARKET CAP
        # =========================================

        if marketcap < cls.MIN_MARKET_CAP:

            hard_reject = True

            reasons.append(
                f"MC BELOW "
                f"${cls.MIN_MARKET_CAP:,.0f}"
            )

        elif marketcap > cls.MAX_MARKET_CAP:

            hard_reject = True

            reasons.append(
                f"MC ABOVE "
                f"${cls.MAX_MARKET_CAP:,.0f}"
            )

        # =========================================
        # BUY PRESSURE
        # =========================================

        if buy_ratio < cls.MIN_BUY_RATIO:

            hard_reject = True

            reasons.append(
                f"BUY RATIO BELOW "
                f"{cls.MIN_BUY_RATIO:.2f}"
            )

        # =========================================
        # VOLUME / MC
        # =========================================

        if volume_ratio < cls.MIN_VOLUME_RATIO:

            hard_reject = True

            reasons.append(
                f"VOLUME/MC BELOW "
                f"{cls.MIN_VOLUME_RATIO:.2f}"
            )

        # =========================================
        # TRANSACTIONS
        # =========================================

        if total_txns < cls.MIN_TXNS:

            hard_reject = True

            reasons.append(
                f"TXNS BELOW "
                f"{cls.MIN_TXNS}"
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
        # HARD REJECTION
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
        # BUY >= 0.55
        # FINAL >= 80
        #
        # Abnormal volume does not automatically
        # reject, but prevents the strongest signal
        # when activity becomes extreme.
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
        # BUY >= 0.55
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
        # =========================================

        if (
            gem_score >= cls.EARLY_GEM_SCORE
            and ai_score >= 55
            and security_quality_ok
            and buy_ratio >= 0.50
            and final_score >= cls.EARLY_GEM_SCORE
        ):

            reasons.append(
                "EARLY ENTRY CANDIDATE"
            )

            return cls._result(
                final_score=final_score,
                should_signal=False,
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

            "reasons": reasons,

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
