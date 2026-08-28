from birdeye import BirdEye
from dexscreener import DexScreener
from rugcheck import RugCheck

from ai.security import SecurityAnalyzer
from ai.momentum import MomentumAnalyzer
from ai.whales import WhaleAnalyzer

from config import RUGCHECK_API_KEY


class TokenAnalyzer:

    def __init__(self, birdeye_api_key):

        self.birdeye = BirdEye(birdeye_api_key)
        self.dex = DexScreener()
        self.rug = RugCheck(RUGCHECK_API_KEY)

        self.security = SecurityAnalyzer()
        self.momentum = MomentumAnalyzer()
        self.whales = WhaleAnalyzer()

    def analyze(self, token_address):

        token = self.birdeye.token_overview(token_address)

        if not token:
            return {
                "success": False,
                "message": "Token not found"
            }

        dex = self.dex.token_info(token_address)
        security = self.security.analyze(token)
        momentum = self.momentum.analyze(token)
        whale = self.whales.analyze(token)
        rug = self.rug.report(token_address)

        # ---------- AI SCORE ----------

        ai_score = 0

        ai_score += security["score"]          # 0 - 20
        ai_score += momentum["score"]          # 0 - 20
        ai_score += whale["score"]             # 0 - 20

        if rug:

            ai_score += rug["rug_score"]       # 0 - 30

            if rug["verified"]:
                ai_score += 5

            if rug["risk"] == "HIGH":
                ai_score -= 10

            elif rug["risk"] == "MEDIUM":
                ai_score -= 5

        ai_score = max(0, min(ai_score, 100))

        # ---------- SIGNAL ----------

        if ai_score >= 90:
            signal = "STRONG BUY"
            risk = "LOW"

        elif ai_score >= 75:
            signal = "BUY"
            risk = "LOW"

        elif ai_score >= 60:
            signal = "HOLD"
            risk = "MEDIUM"

        elif ai_score >= 40:
            signal = "SELL"
            risk = "HIGH"

        else:
            signal = "AVOID"
            risk = "VERY HIGH"

        return {

            "success": True,

            "name": token.get("name"),
            "symbol": token.get("symbol"),

            "price": token.get("price"),
            "market_cap": token.get("marketCap"),
            "fdv": token.get("fdv"),
            "liquidity": token.get("liquidity"),
            "holders": token.get("holder"),

            "volume_24h": token.get("v24hUSD"),
            "price_change_24h": token.get("priceChange24hPercent"),

            "dex": dex.get("dex") if dex else None,
            "pair": dex.get("pair") if dex else None,
            "pair_liquidity": dex.get("liquidity") if dex else None,
            "pair_volume_24h": dex.get("volume_24h") if dex else None,
            "pair_created": dex.get("pair_created") if dex else None,
            "chart": dex.get("url") if dex else None,

            "security_score": security["score"],
            "security_grade": security["grade"],

            "momentum_score": momentum["score"],
            "momentum_grade": momentum["grade"],
            "trend": momentum["trend"],

            "whale_score": whale["score"],
            "whale_grade": whale["grade"],
            "whale_status": whale["status"],

            "verified": rug["verified"] if rug else False,
            "rug_score": rug["rug_score"] if rug else 0,
            "rug_risk": rug["risk"] if rug else "UNKNOWN",
            "graph_insiders": rug["graph_insiders"] if rug else 0,
            "insider_networks": rug["insider_networks"] if rug else 0,

            "ai_score": ai_score,
            "risk": risk,
            "signal": signal,
        }
