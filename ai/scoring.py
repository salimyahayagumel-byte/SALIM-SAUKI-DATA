class AIScoring:

    @staticmethod
    def _number(value):
        try:
            if value is None:
                return 0.0

            return float(value)

        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def calculate(cls, data):

        score = 0

        liquidity = cls._number(
            data.get("liquidity")
        )

        market_cap = cls._number(
            data.get(
                "market_cap",
                data.get("marketcap")
            )
        )

        volume = cls._number(
            data.get(
                "volume_24h",
                data.get("volume24h")
            )
        )

        price_change = cls._number(
            data.get("price_change_24h")
        )

        buys = cls._number(
            data.get("buys24h")
        )

        sells = cls._number(
            data.get("sells24h")
        )

        # =========================================
        # 1. LIQUIDITY — 25 POINTS
        # =========================================

        if liquidity >= 500_000:
            score += 25

        elif liquidity >= 250_000:
            score += 23

        elif liquidity >= 100_000:
            score += 21

        elif liquidity >= 50_000:
            score += 18

        elif liquidity >= 25_000:
            score += 14

        elif liquidity >= 10_000:
            score += 9

        elif liquidity >= 5_000:
            score += 4

        # =========================================
        # 2. MARKET CAP — 20 POINTS
        # =========================================

        # Small-cap tokens get more points.
        if 10_000 <= market_cap <= 100_000:
            score += 20

        elif 100_000 < market_cap <= 250_000:
            score += 19

        elif 250_000 < market_cap <= 500_000:
            score += 18

        elif 500_000 < market_cap <= 1_000_000:
            score += 16

        elif 1_000_000 < market_cap <= 2_500_000:
            score += 13

        elif 2_500_000 < market_cap <= 5_000_000:
            score += 10

        elif 5_000_000 < market_cap <= 10_000_000:
            score += 6

        elif market_cap > 10_000_000:
            score += 2

        # =========================================
        # 3. VOLUME — 20 POINTS
        # =========================================

        if volume >= 1_000_000:
            score += 20

        elif volume >= 500_000:
            score += 18

        elif volume >= 250_000:
            score += 16

        elif volume >= 100_000:
            score += 14

        elif volume >= 50_000:
            score += 12

        elif volume >= 25_000:
            score += 10

        elif volume >= 10_000:
            score += 8

        elif volume >= 5_000:
            score += 6

        # =========================================
        # 4. PRICE MOMENTUM — 15 POINTS
        # =========================================

        if price_change >= 100:
            score += 15

        elif price_change >= 50:
            score += 14

        elif price_change >= 25:
            score += 12

        elif price_change >= 15:
            score += 10

        elif price_change >= 5:
            score += 8

        elif price_change >= 0:
            score += 6

        elif price_change >= -10:
            score += 3

        elif price_change >= -20:
            score += 1

        # Strong negative momentum gets 0.
        else:
            score += 0

        # =========================================
        # 5. BUY / SELL PRESSURE — 10 POINTS
        # =========================================

        total_txns = buys + sells

        buy_ratio = 0.0

        if total_txns > 0:

            buy_ratio = buys / total_txns

            if buy_ratio >= 0.75:
                score += 10

            elif buy_ratio >= 0.65:
                score += 9

            elif buy_ratio >= 0.60:
                score += 8

            elif buy_ratio >= 0.55:
                score += 7

            elif buy_ratio >= 0.50:
                score += 6

            elif buy_ratio >= 0.45:
                score += 3

            else:
                score += 0

        # =========================================
        # 6. TRANSACTION ACTIVITY — 10 POINTS
        # =========================================

        if total_txns >= 2_000:
            score += 10

        elif total_txns >= 1_000:
            score += 9

        elif total_txns >= 500:
            score += 8

        elif total_txns >= 250:
            score += 7

        elif total_txns >= 100:
            score += 6

        elif total_txns >= 50:
            score += 5

        elif total_txns >= 20:
            score += 3

        else:
            score += 0

        # =========================================
        # SCORE BOUNDS
        # =========================================

        score = max(
            0,
            min(
                int(score),
                100
            )
        )

        # =========================================
        # GRADE
        # =========================================

        if score >= 90:
            grade = "A+"

        elif score >= 80:
            grade = "A"

        elif score >= 70:
            grade = "B"

        elif score >= 60:
            grade = "C"

        elif score >= 50:
            grade = "D"

        elif score >= 35:
            grade = "E"

        else:
            grade = "F"

        # =========================================
        # SIGNAL
        # =========================================

        if score >= 85:

            signal = "🔥 STRONG BUY WATCH"

        elif score >= 75:

            signal = "🚀 BUY WATCH"

        elif score >= 65:

            signal = "🟢 WATCH"

        elif score >= 50:

            signal = "🟡 NEUTRAL"

        elif score >= 35:

            signal = "🟠 HIGH RISK"

        else:

            signal = "🔴 AVOID"

        return {
            "score": score,

            "grade": grade,

            "signal": signal,

            "liquidity": liquidity,

            "market_cap": market_cap,

            "volume_24h": volume,

            "price_change_24h": price_change,

            "buys24h": int(buys),

            "sells24h": int(sells),

            "buy_ratio": buy_ratio,

            "total_txns": int(total_txns),
        }
