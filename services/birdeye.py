import httpx
from config import BIRDEYE_API_KEY

BASE_URL = "https://public-api.birdeye.so"


class BirdEye:

    def __init__(self):
        self.headers = {
            "X-API-KEY": BIRDEYE_API_KEY,
            "Accept": "application/json",
        }

    async def get_token_overview(self, token_address: str):
        async with httpx.AsyncClient(
            timeout=30,
            http2=False,
            verify=True,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                f"{BASE_URL}/defi/token_overview",
                headers=self.headers,
                params={"address": token_address},
            )

            print(response.status_code)
            print(response.text)

            response.raise_for_status()
            return response.json()
