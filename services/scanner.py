from services.dexscreener import DexScreener


class TokenScanner:

    def __init__(self):
        self.dex = DexScreener()

    async def scan(self, query="sol"):
        pairs = await self.dex.search(query)

        results = []

        for pair in pairs:

            if pair.get("chainId") != "solana":
                continue

            results.append({
                "name": pair["baseToken"]["name"],
                "symbol": pair["baseToken"]["symbol"],
                "address": pair["baseToken"]["address"],
                "price": pair.get("priceUsd"),
                "liquidity": pair.get("liquidity", {}).get("usd"),
                "volume24h": pair.get("volume", {}).get("h24"),
                "marketcap": pair.get("fdv"),
                "dex": pair.get("dexId"),
            })

        return results
