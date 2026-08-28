class MomentumAnalyzer:

    def analyze(self, token):

        score = 0

        result = {}

        volume = token.get("v24hUSD") or 0
        liquidity = token.get("liquidity") or 0
        holders = token.get("holder") or 0
        change = token.get("priceChange24hPercent") or 0

        # Volume
        if volume >= 1000000:
            score += 5
            result["volume"] = "VERY HIGH"

        elif volume >= 100000:
            score += 4
            result["volume"] = "HIGH"

        elif volume >= 10000:
            score += 2
            result["volume"] = "MEDIUM"

        else:
            result["volume"] = "LOW"

        # Liquidity
        if liquidity >= 1000000:
            score += 5

        elif liquidity >= 100000:
            score += 4

        elif liquidity >= 10000:
            score += 2

        # Holders
        if holders >= 100000:
            score += 5

        elif holders >= 10000:
            score += 4

        elif holders >= 1000:
            score += 3

        # Price Trend
        if change >= 20:
            score += 5

        elif change >= 10:
            score += 4

        elif change >= 0:
            score += 3

        elif change >= -10:
            score += 2

        if score >= 18:
            grade = "A"
            trend = "BULLISH"

        elif score >= 14:
            grade = "B"
            trend = "UPTREND"

        elif score >= 10:
            grade = "C"
            trend = "SIDEWAYS"

        else:
            grade = "D"
            trend = "BEARISH"

        result["score"] = score
        result["grade"] = grade
        result["trend"] = trend

        return result
