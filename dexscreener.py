import requests


class DexScreener:
    BASE_URL = "https://api.dexscreener.com/latest/dex/tokens"

    def token_info(self, address):
        try:
            url = f"{self.BASE_URL}/{address}"
            response = requests.get(url, timeout=20)
            response.raise_for_status()

            data = response.json()

            pairs = data.get("pairs", [])
            if not pairs:
                return None

            # Zaɓi pair mafi girman liquidity
            pair = max(
                pairs,
                key=lambda p: p.get("liquidity", {}).get("usd", 0)
            )

            return {
                "dex": pair.get("dexId"),
                "pair": pair.get("pairAddress"),
                "chain": pair.get("chainId"),
                "price_usd": pair.get("priceUsd"),
                "liquidity": pair.get("liquidity", {}).get("usd"),
                "fdv": pair.get("fdv"),
                "market_cap": pair.get("marketCap"),
                "buys_24h": pair.get("txns", {}).get("h24", {}).get("buys"),
                "sells_24h": pair.get("txns", {}).get("h24", {}).get("sells"),
                "volume_24h": pair.get("volume", {}).get("h24"),
                "pair_created": pair.get("pairCreatedAt"),
                "url": pair.get("url"),
            }

        except Exception as e:
            print("DexScreener Error:", e)
            return None
