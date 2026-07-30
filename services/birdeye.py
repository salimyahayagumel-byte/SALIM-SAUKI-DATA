import httpx

from config import BIRDEYE_API_KEY


BASE_URL = "https://public-api.birdeye.so"


class BirdEye:

    def __init__(self):
        self.headers = {
            "X-API-KEY": BIRDEYE_API_KEY,
            "accept": "application/json"
        }

    async def get_token_overview(self, token_address: str):
        url = f"{BASE_URL}/defi/token_overview"

        params = {
            "address": token_address
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                headers=self.headers,
                params=params
            )

            response.raise_for_status()

            return response.json()
