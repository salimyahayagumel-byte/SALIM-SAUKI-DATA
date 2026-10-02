"""
SALIM SAUKI DATA V10
SAFE API HEALTH CHECK

Run:
    python check_apis.py

This script never prints API keys or full secret-bearing URLs.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


def safe_endpoint(url: str) -> str:
    text = str(url or "")
    if "?" in text:
        return text.split("?", 1)[0] + "?***HIDDEN***"
    return text


def test_http(name, method, url, headers=None, json_body=None, timeout=12):
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=timeout,
        )
        body = response.text[:180].replace("\n", " ")
        print(f"🟢 {name}: HTTP {response.status_code} | {body}")
        return True
    except Exception as exc:
        print(f"🔴 {name}: {type(exc).__name__} | {exc}")
        return False


def rpc_test(name, url, method, params=None, timeout=12):
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            print(f"🔴 {name}: RPC ERROR | {data['error']}")
            return False

        print(
            f"🟢 {name}: HTTP {response.status_code} | "
            f"JSON-RPC OK"
        )
        return True

    except Exception as exc:
        print(f"🔴 {name}: {type(exc).__name__} | {exc}")
        return False


def main():
    print("=" * 60)
    print("SALIM SAUKI DATA — V10 API HEALTH CHECK")
    print("=" * 60)

    results = {}

    # DexScreener
    results["DexScreener"] = test_http(
        "DexScreener",
        "GET",
        "https://api.dexscreener.com/latest/dex/search?q=SOL",
    )

    # Solana endpoints
    solana_urls = []

    flux_url = os.getenv("FLUXRPC_RPC_URL", "").strip()
    flux_key = os.getenv("FLUXRPC_API_KEY", "").strip()

    if not flux_url and flux_key:
        flux_url = f"https://cdn.fluxrpc.com?key={flux_key}"

    if flux_url:
        solana_urls.append(("FluxRPC", flux_url))

    for key in ("SOLANA_RPC_URL", "SOLANA_RPC_URL_2", "SOLANA_RPC_URL_3"):
        value = os.getenv(key, "").strip()
        if value and not any(url == value for _, url in solana_urls):
            solana_urls.append((key, value))

    for name, url in solana_urls:
        results[name] = rpc_test(
            name,
            url,
            "getHealth",
        )

    # Birdeye
    birdeye_key = os.getenv("BIRDEYE_API_KEY", "").strip()
    if birdeye_key:
        results["Birdeye"] = test_http(
            "Birdeye",
            "GET",
            "https://public-api.birdeye.so/defi/price"
            "?address=So11111111111111111111111111111111111111112",
            headers={
                "X-API-KEY": birdeye_key,
                "accept": "application/json",
                "x-chain": "solana",
            },
        )
    else:
        print("🟡 Birdeye: API KEY NOT FOUND")

    # RugCheck
    results["RugCheck"] = test_http(
        "RugCheck",
        "GET",
        "https://api.rugcheck.xyz/v1/stats/new_tokens",
    )

    # Helius
    helius_key = os.getenv("HELIUS_API_KEY", "").strip()
    # Helius is optional when the configured Solana RPCs are healthy.
    # Treat the common placeholder as NOT CONFIGURED rather than a failed
    # production dependency. Never print the key.
    if helius_key and helius_key != "YOUR_HELIUS_API_KEY":
        results["Helius"] = rpc_test(
            "Helius",
            f"https://mainnet.helius-rpc.com/?api-key={helius_key}",
            "getHealth",
        )
    else:
        print("🟡 Helius: NOT CONFIGURED (optional)")

    # Base
    base_urls = []
    for key in ("BASE_RPC_URL", "BASE_RPC_URL_2"):
        value = os.getenv(key, "").strip()
        if value:
            base_urls.append((key, value))

    for name, url in base_urls:
        results[name] = rpc_test(
            name,
            url,
            "eth_blockNumber",
        )

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, ok in results.items():
        print(f"{'🟢' if ok else '🔴'} {name}")

    print("=" * 60)
    print("NOTE: API keys are never printed by this checker.")
    print("=" * 60)


if __name__ == "__main__":
    main()
