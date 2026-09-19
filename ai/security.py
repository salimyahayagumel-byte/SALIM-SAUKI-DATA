class SecurityAnalyzer:

    def analyze(self, token):

        score = 0
        result = {}

        liquidity = token.get("liquidity") or 0
        holders = token.get("holder") or 0
        market_cap = token.get("marketCap") or 0
        volume = token.get("v24hUSD") or 0
        change = token.get("priceChange24hPercent") or 0

        # Liquidity
        if liquidity >= 100000:
            score += 4
            result["liquidity"] = "PASS ✅"
        else:
            result["liquidity"] = "LOW ⚠️"

        # Holders
        if holders >= 1000:
            score += 4
            result["holders"] = "PASS ✅"
        else:
            result["holders"] = "LOW ⚠️"

        # Market Cap
        if market_cap >= 1000000:
            score += 4
            result["market_cap"] = "PASS ✅"
        else:
            result["market_cap"] = "LOW ⚠️"

        # Volume
        if volume >= 100000:
            score += 4
            result["volume"] = "PASS ✅"
        else:
            result["volume"] = "LOW ⚠️"

        # Price Stability
        if change > -20:
            score += 4
            result["price"] = "STABLE ✅"
        else:
            result["price"] = "HIGH RISK ⚠️"

        result["score"] = score

        if score >= 18:
            result["grade"] = "A"

        elif score >= 15:
            result["grade"] = "B"

        elif score >= 10:
            result["grade"] = "C"

        else:
            result["grade"] = "D"

        return result
