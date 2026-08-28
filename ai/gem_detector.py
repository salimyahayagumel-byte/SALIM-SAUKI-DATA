"""
SALIM SAUKI DATA
GEM DETECTOR V3

Purpose:
    Detect high-quality early Solana token candidates.

Main scoring areas:
    - Market cap
    - Liquidity
    - Liquidity / MC
    - Volume
    - Volume / MC
    - Buy pressure
    - Transaction activity
    - Momentum
    - Abnormal-volume / wash-trading caution

This module does NOT guarantee profit.
It only ranks token quality based on available market data.
"""

from typing import Any, Dict, List


class GemDetector:

    # =========================================================
    # SCORE LIMITS
    # =========================================================

    MIN_GEM_SCORE = 0
    MAX_GEM_SCORE = 100

    # =========================================================
    # HARD SAFETY FILTERS
    # =========================================================

    MIN_MARKETCAP = 10_000
    MAX_MARKETCAP = 50_000_000

    MIN_LIQUIDITY = 5_000
    MIN_VOLUME = 5_000
    MIN_TXNS = 20

    MIN_BUY_RATIO = 0.40

    # =========================================================
    # ACTIVITY PROTECTION
    # =========================================================

    # Very high volume/MC can indicate abnormal activity.
    ABNORMAL_VOLUME_RATIO = 10.0
    EXTREME_VOLUME_RATIO = 20.0

    def __init__(self):
        pass

    # =========================================================
    # NUMBER HELPER
    # =========================================================

    @staticmethod
    def _number(value: Any) -> float:

        try:

            if value is None:
                return 0.0

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

    # =========================================================
    # GEM ANALYSIS
    # =========================================================

    def analyze(
        self,
        token: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(token, dict):

            return self._empty_result(
                "INVALID TOKEN DATA"
            )

        # =====================================================
        # BASIC DATA
        # =====================================================

        liquidity = self._number(
            token.get("liquidity")
        )

        marketcap = self._number(
            token.get(
                "marketcap",
                token.get("market_cap")
            )
        )

        volume = self._number(
            token.get(
                "volume24h",
                token.get("volume")
            )
        )

        buys = self._number(
            token.get("buys24h")
        )

        sells = self._number(
            token.get("sells24h")
        )

        price_change = self._number(
            token.get("price_change_24h")
        )

        # =====================================================
        # TRANSACTIONS
        # =====================================================

        supplied_total_txns = self._number(
            token.get("total_txns")
        )

        calculated_total_txns = (
            buys + sells
        )

        if supplied_total_txns > 0:

            total_txns = supplied_total_txns

        else:

            total_txns = calculated_total_txns

        # =====================================================
        # RATIOS
        # =====================================================

        liquidity_ratio = 0.0

        if marketcap > 0:

            liquidity_ratio = (
                liquidity / marketcap
            )

        volume_ratio = 0.0

        if marketcap > 0:

            volume_ratio = (
                volume / marketcap
            )

        buy_ratio = 0.0

        if total_txns > 0:

            if buys > 0 or sells > 0:

                buy_ratio = (
                    buys / total_txns
                )

            else:

                # Preserve an already calculated
                # buy ratio if scanner supplied it.
                buy_ratio = self._number(
                    token.get("buy_ratio")
                )

        # =====================================================
        # SCORE
        # =====================================================

        score = 0

        reasons: List[str] = []

        # =====================================================
        # 1. MARKET CAP
        # MAX +20
        # =====================================================

        if 10_000 <= marketcap <= 100_000:

            score += 20

            reasons.append(
                "VERY SMALL MC"
            )

        elif 100_000 < marketcap <= 250_000:

            score += 19

            reasons.append(
                "SMALL MC"
            )

        elif 250_000 < marketcap <= 500_000:

            score += 18

            reasons.append(
                "SMALL MC"
            )

        elif 500_000 < marketcap <= 1_000_000:

            score += 15

            reasons.append(
                "MID-SMALL MC"
            )

        elif 1_000_000 < marketcap <= 2_500_000:

            score += 11

            reasons.append(
                "MID CAP"
            )

        elif 2_500_000 < marketcap <= 5_000_000:

            score += 7

            reasons.append(
                "LARGER MC"
            )

        elif 5_000_000 < marketcap <= 10_000_000:

            score += 3

            reasons.append(
                "HIGH MC"
            )

        elif 10_000_000 < marketcap <= 50_000_000:

            score += 1

            reasons.append(
                "LARGE MC"
            )

        elif marketcap > 50_000_000:

            score -= 20

            reasons.append(
                "MC TOO HIGH"
            )

        else:

            reasons.append(
                "INVALID MC"
            )

        # =====================================================
        # 2. LIQUIDITY
        # MAX +20
        # =====================================================

        if liquidity >= 500_000:

            score += 20

            reasons.append(
                "EXCELLENT LIQUIDITY"
            )

        elif liquidity >= 250_000:

            score += 18

            reasons.append(
                "STRONG LIQUIDITY"
            )

        elif liquidity >= 100_000:

            score += 16

            reasons.append(
                "GOOD LIQUIDITY"
            )

        elif liquidity >= 50_000:

            score += 14

            reasons.append(
                "HEALTHY LIQUIDITY"
            )

        elif liquidity >= 25_000:

            score += 11

            reasons.append(
                "HEALTHY LIQUIDITY"
            )

        elif liquidity >= 10_000:

            score += 8

            reasons.append(
                "ACCEPTABLE LIQUIDITY"
            )

        elif liquidity >= 5_000:

            score += 4

            reasons.append(
                "LOW LIQUIDITY"
            )

        else:

            score -= 15

            reasons.append(
                "LOW LIQUIDITY"
            )

        # =====================================================
        # 3. LIQUIDITY / MC
        # MAX +15
        # =====================================================

        if liquidity_ratio >= 0.50:

            score += 15

            reasons.append(
                "EXCELLENT LIQ/MC"
            )

        elif liquidity_ratio >= 0.30:

            score += 13

            reasons.append(
                "STRONG LIQ/MC"
            )

        elif liquidity_ratio >= 0.20:

            score += 11

            reasons.append(
                "GOOD LIQ/MC"
            )

        elif liquidity_ratio >= 0.10:

            score += 7

            reasons.append(
                "HEALTHY LIQ/MC"
            )

        elif liquidity_ratio >= 0.05:

            score += 3

            reasons.append(
                "ACCEPTABLE LIQ/MC"
            )

        elif marketcap > 0:

            score -= 5

            reasons.append(
                "WEAK LIQ/MC"
            )

        # =====================================================
        # 4. VOLUME
        # MAX +15
        # =====================================================

        if volume >= 1_000_000:

            score += 15

            reasons.append(
                "EXTREME VOLUME"
            )

        elif volume >= 500_000:

            score += 14

            reasons.append(
                "HIGH VOLUME"
            )

        elif volume >= 250_000:

            score += 13

            reasons.append(
                "HIGH VOLUME"
            )

        elif volume >= 100_000:

            score += 11

            reasons.append(
                "GOOD VOLUME"
            )

        elif volume >= 50_000:

            score += 9

        elif volume >= 25_000:

            score += 7

        elif volume >= 10_000:

            score += 5

        elif volume >= 5_000:

            score += 3

            reasons.append(
                "LOW VOLUME"
            )

        else:

            score -= 10

            reasons.append(
                "VERY LOW VOLUME"
            )

        # =====================================================
        # 5. VOLUME / MC
        # MAX +10
        #
        # IMPORTANT:
        # Extremely high volume/MC is NOT automatically good.
        # It can indicate abnormal trading or wash trading.
        # =====================================================

        if volume_ratio > self.EXTREME_VOLUME_RATIO:

            score -= 12

            reasons.append(
                "EXTREME VOLUME/MC"
            )

            reasons.append(
                "POSSIBLE WASH TRADING"
            )

        elif volume_ratio > self.ABNORMAL_VOLUME_RATIO:

            score -= 7

            reasons.append(
                "ABNORMAL VOLUME/MC"
            )

            reasons.append(
                "HIGH ACTIVITY - CAUTION"
            )

        elif volume_ratio >= 3.00:

            score += 5

            reasons.append(
                "HIGH ACTIVITY - CAUTION"
            )

        elif volume_ratio >= 1.00:

            score += 10

            reasons.append(
                "VERY STRONG ACTIVITY"
            )

        elif volume_ratio >= 0.50:

            score += 9

            reasons.append(
                "HIGH ACTIVITY"
            )

        elif volume_ratio >= 0.25:

            score += 8

            reasons.append(
                "GOOD ACTIVITY"
            )

        elif volume_ratio >= 0.10:

            score += 6

            reasons.append(
                "HEALTHY ACTIVITY"
            )

        elif volume_ratio >= 0.05:

            score += 4

        elif volume_ratio >= 0.01:

            score += 2

        elif marketcap > 0:

            score -= 3

            reasons.append(
                "LOW ACTIVITY"
            )

        # =====================================================
        # 6. BUY PRESSURE
        # MAX +10
        # =====================================================

        if total_txns <= 0:

            score -= 8

            reasons.append(
                "NO TXNS"
            )

        else:

            if buy_ratio >= 0.75:

                score += 10

                reasons.append(
                    "VERY STRONG BUY PRESSURE"
                )

            elif buy_ratio >= 0.65:

                score += 9

                reasons.append(
                    "STRONG BUY PRESSURE"
                )

            elif buy_ratio >= 0.60:

                score += 8

                reasons.append(
                    "GOOD BUY PRESSURE"
                )

            elif buy_ratio >= 0.55:

                score += 7

                reasons.append(
                    "BUY PRESSURE"
                )

            elif buy_ratio >= 0.50:

                score += 5

                reasons.append(
                    "BALANCED BUY PRESSURE"
                )

            elif buy_ratio >= 0.45:

                score += 2

                reasons.append(
                    "WEAK BUY PRESSURE"
                )

            else:

                score -= 8

                reasons.append(
                    "STRONG SELL PRESSURE"
                )

        # =====================================================
        # 7. TRANSACTION ACTIVITY
        # =====================================================

        if total_txns >= 2_000:

            reasons.append(
                "VERY ACTIVE"
            )

        elif total_txns >= 1_000:

            reasons.append(
                "HIGH TXNS"
            )

        elif total_txns >= 500:

            reasons.append(
                "GOOD TXNS"
            )

        elif total_txns >= 250:

            reasons.append(
                "ACTIVE TXNS"
            )

        elif total_txns >= 100:

            reasons.append(
                "MODERATE TXNS"
            )

        elif total_txns >= 50:

            reasons.append(
                "LOW-MODERATE TXNS"
            )

        else:

            reasons.append(
                "LOW TXNS"
            )

        # =====================================================
        # 8. MOMENTUM
        # MAX +10
        # =====================================================

        if price_change >= 100:

            score += 10

            reasons.append(
                "EXTREME MOMENTUM"
            )

        elif price_change >= 50:

            score += 9

            reasons.append(
                "STRONG MOMENTUM"
            )

        elif price_change >= 25:

            score += 8

            reasons.append(
                "GOOD MOMENTUM"
            )

        elif price_change >= 10:

            score += 6

            reasons.append(
                "POSITIVE MOMENTUM"
            )

        elif price_change >= 0:

            score += 4

        elif price_change >= -10:

            score += 1

        elif price_change >= -20:

            score -= 3

            reasons.append(
                "NEGATIVE MOMENTUM"
            )

        else:

            score -= 8

            reasons.append(
                "VERY NEGATIVE MOMENTUM"
            )

        # =====================================================
        # HARD REJECTION
        # =====================================================

        rejected = False

        reject_reasons: List[str] = []

        # -----------------------------------------------------
        # Invalid market cap
        # -----------------------------------------------------

        if marketcap <= 0:

            rejected = True

            reject_reasons.append(
                "INVALID MC"
            )

        # -----------------------------------------------------
        # Market cap too high
        # -----------------------------------------------------

        if marketcap > self.MAX_MARKETCAP:

            rejected = True

            reject_reasons.append(
                "MC TOO HIGH"
            )

        # -----------------------------------------------------
        # Liquidity
        # -----------------------------------------------------

        if liquidity < self.MIN_LIQUIDITY:

            rejected = True

            reject_reasons.append(
                "LIQUIDITY TOO LOW"
            )

        # -----------------------------------------------------
        # Volume
        # -----------------------------------------------------

        if volume < self.MIN_VOLUME:

            rejected = True

            reject_reasons.append(
                "VOLUME TOO LOW"
            )

        # -----------------------------------------------------
        # Transactions
        # -----------------------------------------------------

        if total_txns < self.MIN_TXNS:

            rejected = True

            reject_reasons.append(
                "TXNS TOO LOW"
            )

        # -----------------------------------------------------
        # Buy pressure
        # -----------------------------------------------------

        if (
            total_txns > 0
            and buy_ratio < self.MIN_BUY_RATIO
        ):

            rejected = True

            reject_reasons.append(
                "SELL PRESSURE"
            )

        # -----------------------------------------------------
        # Extreme abnormal activity
        # -----------------------------------------------------

        if volume_ratio > self.EXTREME_VOLUME_RATIO:

            reject_reasons.append(
                "EXTREME VOLUME/MC"
            )

        # =====================================================
        # SCORE LIMIT
        # =====================================================

        score = max(
            self.MIN_GEM_SCORE,
            min(
                int(score),
                self.MAX_GEM_SCORE,
            )
        )

        # =====================================================
        # GEM LEVEL
        # =====================================================

        if rejected:

            level = "🔴 REJECT"

        elif score >= 85:

            level = "🔥 ELITE GEM"

        elif score >= 75:

            level = "🚀 STRONG GEM"

        elif score >= 65:

            level = "⭐ GEM WATCH"

        elif score >= 55:

            level = "👀 CANDIDATE"

        elif score >= 40:

            level = "⚠️ RISKY"

        else:

            level = "🔴 REJECT"

        # =====================================================
        # SIGNAL
        # =====================================================

        if (
            not rejected
            and score >= 75
        ):

            should_signal = True

            signal = "🔥 GEM SIGNAL"

        elif (
            not rejected
            and score >= 65
        ):

            should_signal = False

            signal = "⭐ GEM WATCH"

        elif (
            not rejected
            and score >= 55
        ):

            should_signal = False

            signal = "👀 CANDIDATE"

        else:

            should_signal = False

            signal = "⛔ NO SIGNAL"

        # =====================================================
        # REJECTION REASONS
        # =====================================================

        if rejected:

            for reason in reject_reasons:

                if reason not in reasons:

                    reasons.append(
                        reason
                    )

        # =====================================================
        # ACTIVITY CLASSIFICATION
        # =====================================================

        if volume_ratio > self.EXTREME_VOLUME_RATIO:

            activity_level = (
                "🔴 EXTREME"
            )

        elif volume_ratio > self.ABNORMAL_VOLUME_RATIO:

            activity_level = (
                "🟠 ABNORMAL"
            )

        elif volume_ratio >= 3:

            activity_level = (
                "🟡 VERY HIGH"
            )

        elif volume_ratio >= 1:

            activity_level = (
                "🟢 HIGH"
            )

        elif volume_ratio >= 0.25:

            activity_level = (
                "🟢 HEALTHY"
            )

        else:

            activity_level = (
                "⚪ LOW"
            )

        # =====================================================
        # MARKET CAP CLASSIFICATION
        # =====================================================

        if 10_000 <= marketcap <= 100_000:

            market_stage = "MICRO CAP"

        elif 100_000 < marketcap <= 250_000:

            market_stage = "SMALL CAP"

        elif 250_000 < marketcap <= 500_000:

            market_stage = "SMALL CAP"

        elif 500_000 < marketcap <= 1_000_000:

            market_stage = "MID-SMALL CAP"

        elif 1_000_000 < marketcap <= 5_000_000:

            market_stage = "MID CAP"

        elif marketcap > 5_000_000:

            market_stage = "LARGE CAP"

        else:

            market_stage = "UNKNOWN"

        # =====================================================
        # RISK CLASSIFICATION
        # =====================================================

        if rejected:

            risk_level = "🔴 CRITICAL"

        elif volume_ratio > self.EXTREME_VOLUME_RATIO:

            risk_level = "🔴 EXTREME"

        elif volume_ratio > self.ABNORMAL_VOLUME_RATIO:

            risk_level = "🟠 HIGH"

        elif buy_ratio < 0.50:

            risk_level = "🟠 HIGH"

        elif liquidity_ratio < 0.10:

            risk_level = "🟠 HIGH"

        elif score < 60:

            risk_level = "🟡 MEDIUM"

        elif score < 75:

            risk_level = "🟡 MEDIUM"

        else:

            risk_level = "🟢 LOW"

        # =====================================================
        # RETURN
        # =====================================================

        return {

            "gem_score": score,

            "gem_level": level,

            "should_signal": should_signal,

            "signal": signal,

            "gem_reasons": reasons,

            "reject_reasons": reject_reasons,

            "rejected": rejected,

            "liquidity_ratio": liquidity_ratio,

            "volume_ratio": volume_ratio,

            "buy_ratio": buy_ratio,

            "total_txns": int(total_txns),

            "market_stage": market_stage,

            "activity_level": activity_level,

            "risk_level": risk_level,

            "marketcap": marketcap,

            "liquidity": liquidity,

            "volume24h": volume,

            "price_change_24h": price_change,
        }

    # =========================================================
    # EMPTY RESULT
    # =========================================================

    @staticmethod
    def _empty_result(
        reason: str,
    ) -> Dict[str, Any]:

        return {

            "gem_score": 0,

            "gem_level": "🔴 REJECT",

            "should_signal": False,

            "signal": "⛔ NO SIGNAL",

            "gem_reasons": [
                reason
            ],

            "reject_reasons": [
                reason
            ],

            "rejected": True,

            "liquidity_ratio": 0.0,

            "volume_ratio": 0.0,

            "buy_ratio": 0.0,

            "total_txns": 0,

            "market_stage": "UNKNOWN",

            "activity_level": "⚪ UNKNOWN",

            "risk_level": "🔴 CRITICAL",

            "marketcap": 0.0,

            "liquidity": 0.0,

            "volume24h": 0.0,

            "price_change_24h": 0.0,
        }


# =============================================================
# BACKWARD-COMPATIBLE ALIAS
# =============================================================

GemDetectorV2 = GemDetector


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    detector = GemDetector()

    test_tokens = [

        {
            "name": "Example Gem",
            "symbol": "GEM",
            "marketcap": 150_000,
            "liquidity": 45_000,
            "volume24h": 250_000,
            "buys24h": 700,
            "sells24h": 300,
            "price_change_24h": 25,
        },

        {
            "name": "Abnormal Volume",
            "symbol": "WASH",
            "marketcap": 50_000,
            "liquidity": 20_000,
            "volume24h": 1_500_000,
            "buys24h": 600,
            "sells24h": 400,
            "price_change_24h": 10,
        },

    ]

    print("=" * 80)
    print(
        "SALIM SAUKI DATA — GEM DETECTOR V3 TEST"
    )
    print("=" * 80)

    for token in test_tokens:

        result = detector.analyze(token)

        print()
        print(
            f"${token['symbol']} "
            f"| GEM={result['gem_score']} "
            f"| {result['gem_level']} "
            f"| {result['signal']}"
        )

        print(
            f"MC=${token['marketcap']:,.0f} | "
            f"LP=${token['liquidity']:,.0f} | "
            f"VOL=${token['volume24h']:,.0f}"
        )

        print(
            f"BUY={result['buy_ratio']:.3f} | "
            f"VOL/MC={result['volume_ratio']:.3f} | "
            f"TXNS={result['total_txns']}"
        )

        print(
            "REASONS:",
            " | ".join(
                result["gem_reasons"][:10]
            )
        )
