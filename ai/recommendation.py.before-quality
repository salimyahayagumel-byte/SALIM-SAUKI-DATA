"""
DEX ANALYSIS BOT
AI Recommendation Engine

Wannan module yana bada recommendation daga bayanan token
da sauran AI/security engines suka samar.

Recommendation:
    🔥 STRONG BUY
    🚀 BUY
    👀 WATCH
    ⚠️ HIGH RISK
    ⛔ AVOID
    ⏳ WAIT FOR DATA

NOT FINANCIAL ADVICE.
"""

from typing import Any, Dict, List


class RecommendationEngine:
    """
    AI-based token recommendation engine.

    Wannan engine baya cewa token zai tashi ko ya sauka.
    Yana amfani da metrics da aka riga aka samo domin bada
    quality/risk recommendation.
    """

    # =========================================================
    # THRESHOLDS
    # =========================================================

    STRONG_BUY_SCORE = 85
    BUY_SCORE = 75
    WATCH_SCORE = 60
    HIGH_RISK_SCORE = 45

    MIN_SECURITY_SCORE = 90

    MIN_LIQUIDITY = 10_000
    MIN_VOLUME = 5_000
    MIN_TXNS = 20

    # =========================================================
    # NUMBER HELPER
    # =========================================================

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        """
        Safely convert value to float.
        """

        try:
            if value is None:
                return default

            return float(value)

        except (TypeError, ValueError):
            return default

    # =========================================================
    # BOOL HELPER
    # =========================================================

    @staticmethod
    def _bool(value: Any) -> bool:
        """
        Safely convert common values to bool.
        """

        if isinstance(value, bool):
            return value

        if isinstance(value, str):

            return value.strip().lower() in {
                "true",
                "1",
                "yes",
                "y",
                "pass",
                "passed",
            }

        if isinstance(value, (int, float)):
            return value != 0

        return False

    # =========================================================
    # MAIN METHOD
    # =========================================================

    @classmethod
    def recommend(cls, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a recommendation for a token.

        Expected token fields include:

            ai_score
            gem_score
            security_score
            security_should_pass
            liquidity
            marketcap
            volume24h
            total_txns
            buy_ratio
            liquidity_ratio
            volume_ratio
            price_change_24h
            final_score
            final_should_signal
        """

        if not isinstance(token, dict):
            return cls._empty_result(
                "INVALID TOKEN DATA"
            )

        # =====================================================
        # READ DATA
        # =====================================================

        symbol = str(
            token.get("symbol")
            or "N/A"
        )

        name = str(
            token.get("name")
            or symbol
        )

        ai_score = cls._number(
            token.get("ai_score")
        )

        gem_score = cls._number(
            token.get("gem_score")
        )

        security_score = cls._number(
            token.get("security_score")
        )

        final_score = cls._number(
            token.get("final_score")
        )

        liquidity = cls._number(
            token.get("liquidity")
        )

        marketcap = cls._number(
            token.get("marketcap")
        )

        volume = cls._number(
            token.get("volume24h")
        )

        total_txns = cls._number(
            token.get("total_txns")
        )

        buy_ratio = cls._number(
            token.get("buy_ratio")
        )

        liquidity_ratio = cls._number(
            token.get("liquidity_ratio")
        )

        volume_ratio = cls._number(
            token.get("volume_ratio")
        )

        price_change = cls._number(
            token.get("price_change_24h")
        )

        security_pass = cls._bool(
            token.get(
                "security_should_pass",
                token.get(
                    "should_pass",
                    False
                )
            )
        )

        final_should_signal = cls._bool(
            token.get(
                "final_should_signal"
            )
        )

        # =====================================================
        # SCORE
        # =====================================================

        recommendation_score = cls._calculate_score(
            ai_score=ai_score,
            gem_score=gem_score,
            security_score=security_score,
            final_score=final_score,
            liquidity=liquidity,
            marketcap=marketcap,
            volume=volume,
            total_txns=total_txns,
            buy_ratio=buy_ratio,
            liquidity_ratio=liquidity_ratio,
            volume_ratio=volume_ratio,
            price_change=price_change,
        )

        # =====================================================
        # HARD SAFETY CHECKS
        # =====================================================

        hard_reject = False
        risk_flags: List[str] = []

        chain = str(
            token.get("chain")
            or ""
        ).lower()

        if chain and chain != "solana":

            hard_reject = True

            risk_flags.append(
                "NON-SOLANA TOKEN"
            )

        if security_score < cls.MIN_SECURITY_SCORE:

            hard_reject = True

            risk_flags.append(
                "SECURITY BELOW 90"
            )

        if not security_pass:

            hard_reject = True

            risk_flags.append(
                "SECURITY CHECK FAILED"
            )

        if liquidity < cls.MIN_LIQUIDITY:

            risk_flags.append(
                "LOW LIQUIDITY"
            )

        if volume < cls.MIN_VOLUME:

            risk_flags.append(
                "LOW VOLUME"
            )

        if total_txns < cls.MIN_TXNS:

            risk_flags.append(
                "LOW TRANSACTION ACTIVITY"
            )

        if buy_ratio < 0.50:

            risk_flags.append(
                "WEAK BUY PRESSURE"
            )

        if liquidity_ratio < 0.10 and marketcap > 0:

            risk_flags.append(
                "WEAK LIQ/MC"
            )

        if volume_ratio < 0.05 and marketcap > 0:

            risk_flags.append(
                "LOW ACTIVITY"
            )

        if price_change < -20:

            risk_flags.append(
                "STRONG NEGATIVE MOMENTUM"
            )

        # =====================================================
        # RECOMMENDATION
        # =====================================================

        if hard_reject:

            recommendation = "⛔ AVOID"

            action = "AVOID"

            confidence = max(
                0,
                min(
                    100,
                    int(
                        round(
                            security_score * 0.60
                            + recommendation_score * 0.40
                        )
                    )
                )
            )

        elif recommendation_score >= cls.STRONG_BUY_SCORE:

            recommendation = "🔥 STRONG BUY"

            action = "STRONG BUY"

            confidence = min(
                100,
                int(
                    round(
                        recommendation_score
                    )
                )
            )

        elif recommendation_score >= cls.BUY_SCORE:

            recommendation = "🚀 BUY"

            action = "BUY"

            confidence = min(
                100,
                int(
                    round(
                        recommendation_score
                    )
                )
            )

        elif recommendation_score >= cls.WATCH_SCORE:

            recommendation = "👀 WATCH"

            action = "WATCH"

            confidence = min(
                100,
                int(
                    round(
                        recommendation_score
                    )
                )
            )

        elif recommendation_score >= cls.HIGH_RISK_SCORE:

            recommendation = "⚠️ HIGH RISK"

            action = "HIGH RISK"

            confidence = min(
                100,
                int(
                    round(
                        recommendation_score
                    )
                )
            )

        else:

            recommendation = "⛔ AVOID"

            action = "AVOID"

            confidence = min(
                100,
                int(
                    round(
                        recommendation_score
                    )
                )
            )

        # =====================================================
        # FINAL SIGNAL OVERRIDE
        # =====================================================

        if (
            final_should_signal
            and not hard_reject
            and recommendation_score >= cls.BUY_SCORE
        ):

            if recommendation_score >= cls.STRONG_BUY_SCORE:

                recommendation = "🔥 STRONG BUY"
                action = "STRONG BUY"

            else:

                recommendation = "🚀 BUY"
                action = "BUY"

        # =====================================================
        # POSITIVE REASONS
        # =====================================================

        positive_reasons: List[str] = []

        if ai_score >= 80:

            positive_reasons.append(
                "VERY STRONG AI SCORE"
            )

        elif ai_score >= 70:

            positive_reasons.append(
                "STRONG AI SCORE"
            )

        elif ai_score >= 60:

            positive_reasons.append(
                "GOOD AI SCORE"
            )

        if gem_score >= 85:

            positive_reasons.append(
                "ELITE GEM SCORE"
            )

        elif gem_score >= 75:

            positive_reasons.append(
                "STRONG GEM SCORE"
            )

        elif gem_score >= 65:

            positive_reasons.append(
                "PROMISING GEM SCORE"
            )

        if security_score >= 95:

            positive_reasons.append(
                "EXCELLENT SECURITY"
            )

        elif security_score >= 90:

            positive_reasons.append(
                "SECURITY PASSED"
            )

        if liquidity_ratio >= 0.50:

            positive_reasons.append(
                "EXCELLENT LIQ/MC"
            )

        elif liquidity_ratio >= 0.30:

            positive_reasons.append(
                "STRONG LIQ/MC"
            )

        elif liquidity_ratio >= 0.20:

            positive_reasons.append(
                "GOOD LIQ/MC"
            )

        if volume_ratio >= 1.00:

            positive_reasons.append(
                "VERY HIGH ACTIVITY"
            )

        elif volume_ratio >= 0.50:

            positive_reasons.append(
                "HIGH ACTIVITY"
            )

        elif volume_ratio >= 0.25:

            positive_reasons.append(
                "GOOD ACTIVITY"
            )

        if buy_ratio >= 0.70:

            positive_reasons.append(
                "VERY STRONG BUY PRESSURE"
            )

        elif buy_ratio >= 0.60:

            positive_reasons.append(
                "STRONG BUY PRESSURE"
            )

        elif buy_ratio >= 0.55:

            positive_reasons.append(
                "POSITIVE BUY PRESSURE"
            )

        if price_change >= 50:

            positive_reasons.append(
                "STRONG MOMENTUM"
            )

        elif price_change >= 20:

            positive_reasons.append(
                "POSITIVE MOMENTUM"
            )

        # =====================================================
        # MARKET CAP CLASSIFICATION
        # =====================================================

        if 10_000 <= marketcap <= 100_000:

            market_stage = "MICRO CAP"

        elif 100_000 < marketcap <= 250_000:

            market_stage = "SMALL CAP"

        elif 250_000 < marketcap <= 1_000_000:

            market_stage = "LOW CAP"

        elif 1_000_000 < marketcap <= 5_000_000:

            market_stage = "MID SMALL CAP"

        elif marketcap > 5_000_000:

            market_stage = "LARGER CAP"

        else:

            market_stage = "UNKNOWN"

        # =====================================================
        # RISK LEVEL
        # =====================================================

        risk_level = cls._risk_level(
            security_score=security_score,
            liquidity=liquidity,
            liquidity_ratio=liquidity_ratio,
            volume=volume,
            buy_ratio=buy_ratio,
            price_change=price_change,
            recommendation_score=recommendation_score,
            hard_reject=hard_reject,
        )

        # =====================================================
        # SUMMARY
        # =====================================================

        summary = cls._summary(
            symbol=symbol,
            recommendation=recommendation,
            score=recommendation_score,
            risk_level=risk_level,
            security_score=security_score,
            gem_score=gem_score,
            ai_score=ai_score,
        )

        # =====================================================
        # RETURN
        # =====================================================

        return {

            "symbol": symbol,

            "name": name,

            "recommendation_score": int(
                recommendation_score
            ),

            "recommendation": recommendation,

            "action": action,

            "confidence": int(
                confidence
            ),

            "risk_level": risk_level,

            "market_stage": market_stage,

            "hard_reject": hard_reject,

            "security_pass": security_pass,

            "final_should_signal": final_should_signal,

            "ai_score": int(ai_score),

            "gem_score": int(gem_score),

            "security_score": int(
                security_score
            ),

            "final_score": int(
                final_score
            ),

            "liquidity": liquidity,

            "marketcap": marketcap,

            "volume24h": volume,

            "total_txns": int(
                total_txns
            ),

            "buy_ratio": buy_ratio,

            "liquidity_ratio": liquidity_ratio,

            "volume_ratio": volume_ratio,

            "price_change_24h": price_change,

            "positive_reasons": positive_reasons,

            "risk_flags": risk_flags,

            "summary": summary,

            "is_recommended": (
                not hard_reject
                and action in {
                    "BUY",
                    "STRONG BUY",
                }
            ),
        }

    # =========================================================
    # SCORE CALCULATION
    # =========================================================

    @classmethod
    def _calculate_score(
        cls,
        ai_score: float,
        gem_score: float,
        security_score: float,
        final_score: float,
        liquidity: float,
        marketcap: float,
        volume: float,
        total_txns: float,
        buy_ratio: float,
        liquidity_ratio: float,
        volume_ratio: float,
        price_change: float,
    ) -> int:
        """
        Calculate recommendation score.

        Weights:

            AI       25%
            GEM      30%
            SECURITY 25%
            FINAL    20%

        Market metrics then apply small quality adjustments.
        """

        # -----------------------------------------------------
        # Base score
        # -----------------------------------------------------

        score = (
            ai_score * 0.25
            + gem_score * 0.30
            + security_score * 0.25
            + final_score * 0.20
        )

        # -----------------------------------------------------
        # Liquidity quality
        # -----------------------------------------------------

        if liquidity_ratio >= 0.50:

            score += 4

        elif liquidity_ratio >= 0.30:

            score += 3

        elif liquidity_ratio >= 0.20:

            score += 2

        elif liquidity_ratio < 0.10 and marketcap > 0:

            score -= 4

        # -----------------------------------------------------
        # Volume quality
        # -----------------------------------------------------

        if volume_ratio >= 1.00:

            score += 4

        elif volume_ratio >= 0.50:

            score += 3

        elif volume_ratio >= 0.25:

            score += 2

        elif volume_ratio < 0.05 and marketcap > 0:

            score -= 3

        # -----------------------------------------------------
        # Buy pressure
        # -----------------------------------------------------

        if buy_ratio >= 0.70:

            score += 4

        elif buy_ratio >= 0.60:

            score += 3

        elif buy_ratio >= 0.55:

            score += 2

        elif buy_ratio < 0.45:

            score -= 5

        # -----------------------------------------------------
        # Transaction activity
        # -----------------------------------------------------

        if total_txns >= 2_000:

            score += 3

        elif total_txns >= 1_000:

            score += 2

        elif total_txns >= 500:

            score += 1

        elif total_txns < 20:

            score -= 5

        # -----------------------------------------------------
        # Momentum
        # -----------------------------------------------------

        if price_change >= 100:

            score += 3

        elif price_change >= 50:

            score += 2

        elif price_change >= 20:

            score += 1

        elif price_change <= -30:

            score -= 5

        elif price_change <= -20:

            score -= 3

        # -----------------------------------------------------
        # Clamp
        # -----------------------------------------------------

        return max(
            0,
            min(
                int(round(score)),
                100
            )
        )

    # =========================================================
    # RISK LEVEL
    # =========================================================

    @staticmethod
    def _risk_level(
        security_score: float,
        liquidity: float,
        liquidity_ratio: float,
        volume: float,
        buy_ratio: float,
        price_change: float,
        recommendation_score: int,
        hard_reject: bool,
    ) -> str:

        if hard_reject:

            return "🔴 CRITICAL"

        if security_score < 60:

            return "🔴 CRITICAL"

        if security_score < 90:

            return "🟠 HIGH"

        if liquidity < 10_000:

            return "🟠 HIGH"

        if liquidity_ratio < 0.10:

            return "🟠 HIGH"

        if volume < 5_000:

            return "🟠 HIGH"

        if buy_ratio < 0.45:

            return "🟠 HIGH"

        if price_change <= -30:

            return "🟠 HIGH"

        if recommendation_score < 60:

            return "🟡 MEDIUM"

        if recommendation_score < 75:

            return "🟡 MEDIUM"

        return "🟢 LOW"

    # =========================================================
    # SUMMARY
    # =========================================================

    @staticmethod
    def _summary(
        symbol: str,
        recommendation: str,
        score: int,
        risk_level: str,
        security_score: float,
        gem_score: float,
        ai_score: float,
    ) -> str:

        return (
            f"${symbol}: "
            f"{recommendation} | "
            f"Score {score}/100 | "
            f"Risk {risk_level} | "
            f"AI {int(ai_score)}/100 | "
            f"GEM {int(gem_score)}/100 | "
            f"SEC {int(security_score)}/100"
        )

    # =========================================================
    # EMPTY RESULT
    # =========================================================

    @staticmethod
    def _empty_result(
        reason: str
    ) -> Dict[str, Any]:

        return {
            "symbol": "N/A",
            "name": "Unknown",

            "recommendation_score": 0,

            "recommendation": "⏳ WAIT FOR DATA",

            "action": "WAIT",

            "confidence": 0,

            "risk_level": "⚪ UNKNOWN",

            "market_stage": "UNKNOWN",

            "hard_reject": True,

            "security_pass": False,

            "final_should_signal": False,

            "ai_score": 0,

            "gem_score": 0,

            "security_score": 0,

            "final_score": 0,

            "liquidity": 0,

            "marketcap": 0,

            "volume24h": 0,

            "total_txns": 0,

            "buy_ratio": 0,

            "liquidity_ratio": 0,

            "volume_ratio": 0,

            "price_change_24h": 0,

            "positive_reasons": [],

            "risk_flags": [
                reason
            ],

            "summary": (
                f"⏳ WAIT FOR DATA: {reason}"
            ),

            "is_recommended": False,
        }


# =============================================================
# BACKWARD-COMPATIBLE HELPER
# =============================================================

def recommend_token(
    token: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Simple helper function.

    Example:

        result = recommend_token(token)

        print(result["recommendation"])
    """

    return RecommendationEngine.recommend(
        token
    )


# =============================================================
# ALIAS
# =============================================================

Recommendation = RecommendationEngine


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    sample_token = {

        "name": "Sol",

        "symbol": "SOL",

        "chain": "solana",

        "ai_score": 71,

        "gem_score": 73,

        "security_score": 100,

        "security_should_pass": True,

        "final_score": 79,

        "final_should_signal": True,

        "marketcap": 174_978,

        "liquidity": 78_989,

        "volume24h": 17_566,

        "total_txns": 147,

        "buy_ratio": 0.605,

        "liquidity_ratio": 0.451,

        "volume_ratio": 0.100,

        "price_change_24h": 0,
    }

    result = RecommendationEngine.recommend(
        sample_token
    )

    print("=" * 70)
    print(
        "DEX ANALYSIS BOT — "
        "RECOMMENDATION ENGINE"
    )
    print("=" * 70)

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )
