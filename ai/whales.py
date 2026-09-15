"""Market-support heuristic used by the legacy analysis endpoint.

Important: this module does NOT observe individual wallets, whale flows,
large transfers, or smart-money addresses.  It only estimates market
support from aggregate holder count, liquidity, and market cap.
"""


class WhaleAnalyzer:

    def analyze(self, token):

        token = token if isinstance(token, dict) else {}

        holders = token.get("holder") or token.get("holders") or 0
        liquidity = token.get("liquidity") or 0
        marketcap = (
            token.get("marketCap")
            or token.get("market_cap")
            or token.get("marketcap")
            or 0
        )

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
            status = "STRONG MARKET SUPPORT"
        elif score >= 14:
            grade = "B"
            status = "GOOD MARKET SUPPORT"
        elif score >= 10:
            grade = "C"
            status = "AVERAGE MARKET SUPPORT"
        else:
            grade = "D"
            status = "WEAK MARKET SUPPORT"

        return {
            "score": score,
            "grade": grade,
            "status": status,
            "is_actual_whale_analysis": False,
            "method": "aggregate market-support heuristic",
        }
