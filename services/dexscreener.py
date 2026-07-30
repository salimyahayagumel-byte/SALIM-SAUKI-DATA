import httpx


BASE_URL = "https://api.dexscreener.com/latest/dex/search"


class DexScreener:

    async def search(self, query: str):
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                BASE_URL,
                params={"q": query}
            )

            response.raise_for_status()

            data = response.json()

            return data.get("pairs", [])
