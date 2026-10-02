import requests


class RugCheck:

    BASE_URL = "https://api.rugcheck.xyz/v1"

    def __init__(self, api_key):
        self.api_key = api_key

    def report(self, token_address):

        try:

            url = f"{self.BASE_URL}/tokens/{token_address}/report"

            headers = {
                "X-API-KEY": self.api_key,
                "accept": "application/json",
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

            verification = data.get("verification", {})
            insiders = data.get("insiderNetworks", [])
            graph = data.get("graphInsidersDetected", 0)
            launchpad = data.get("launchpad")

            verified = bool(verification)

            score = 20

            if verified:
                score += 5

            if len(insiders) == 0:
                score += 5
            elif len(insiders) <= 2:
                score += 3
            elif len(insiders) <= 5:
                score += 1
            else:
                score -= 3

            # Rage maki ne kawai idan graph ya yi matuƙar yawa
            if graph > 50000:
                score -= 3

            score = max(0, min(score, 30))

            if score >= 25:
                risk = "LOW"
            elif score >= 18:
                risk = "MEDIUM"
            else:
                risk = "HIGH"

            return {
                "success": True,
                "verified": verified,
                "mint": verification.get("mint"),
                "graph_insiders": graph,
                "insider_networks": len(insiders),
                "launchpad": launchpad,
                "rug_score": score,
                "risk": risk,
            }

        except Exception as e:
            print("RugCheck Error:", e)
            return None
