import requests

BASE_URL = "https://public-api.birdeye.so"

class BirdEye:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-API-KEY": api_key,
            "accept": "application/json"
        }

    def token_overview(self, address: str):
        url = f"{BASE_URL}/defi/token_overview?address={address}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=20
            )

            response.raise_for_status()

            result = response.json()

            if not result.get("success"):
                return None

            return result["data"]

        except Exception as e:
            print(f"BirdEye Error: {e}")
            return None
