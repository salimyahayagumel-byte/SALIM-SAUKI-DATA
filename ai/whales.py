class WhaleAnalyzer:

    def analyze(self, token):

        holders = token.get("holder") or 0
        liquidity = token.get("liquidity") or 0
        marketcap = token.get("marketCap") or 0

        score = 0

        if holders >= 500000:
            score += 8
        elif holders >= 100000:
            score += 6
        elif holders >= 10000:
            score += 4
        else:
            score += 2

        if liquidity >= 1000000:
            score += 6
        elif liquidity >= 100000:
            score += 4
        else:
            score += 2

        if marketcap >= 100000000:
            score += 6
        elif marketcap >= 10000000:
            score += 4
        else:
            score += 2

        if score >= 18:
            grade = "A"
            status = "STRONG WHALE SUPPORT"
        elif score >= 14:
            grade = "B"
            status = "GOOD WHALE SUPPORT"
        elif score >= 10:
            grade = "C"
            status = "AVERAGE"
        else:
            grade = "D"
            status = "WEAK"

        return {
            "score": score,
            "grade": grade,
            "status": status,
        }
