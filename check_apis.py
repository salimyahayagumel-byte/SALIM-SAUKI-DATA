"""
MASFOX
V10 API / RPC Health Checker

Rules:
- Never print API keys, BOT_TOKEN, chat IDs, or full authenticated URLs.
- Solana JSON-RPC: getSlot
- FluxRPC: getSlot
- EVM RPCs: eth_chainId
- Optional Solana RPC 2/3 are informational when missing.
"""

import json
import os
import sys
from urllib.parse import urlsplit, parse_qs

import requests

import config


TIMEOUT = 15


def configured(value):
    return bool(str(value or "").strip())


def safe_url(url):
    """Return a URL safe for terminal output."""
    if not url:
        return ""

    try:
        p = urlsplit(str(url))
        host = p.netloc or "unknown-host"

        # Never display query strings because they may contain API keys.
        path = p.path or "/"

        return f"{p.scheme}://{host}{path}"
    except Exception:
        return "<invalid-url>"


def rpc_url_with_flux_key():
    """
    Get the effective FluxRPC URL.

    config.py should normally build this already, but this extra guard
    keeps the checker compatible with older .env/config combinations.
    """
    url = str(getattr(config, "FLUXRPC_RPC_URL", "") or "").strip()
    key = str(getattr(config, "FLUXRPC_API_KEY", "") or "").strip()

    if not url and key:
        return f"https://eu.fluxrpc.com?key={key}"

    if url and key:
        try:
            query = parse_qs(urlsplit(url).query)
            if not query.get("key"):
                separator = "&" if "?" in url else "?"
                return f"{url}{separator}key={key}"
        except Exception:
            pass

    return url


def post_jsonrpc(url, method, params=None):
    """Perform JSON-RPC POST and return structured result."""
    if not url:
        return {
            "ok": False,
            "status": None,
            "error": "NOT CONFIGURED",
            "result": None,
        }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "MASFOX-HealthCheck/10.4",
            },
        )

        status = response.status_code

        try:
            data = response.json()
        except Exception:
            data = None

        if status < 200 or status >= 300:
            return {
                "ok": False,
                "status": status,
                "error": f"HTTP {status}",
                "result": None,
            }

        if not isinstance(data, dict):
            return {
                "ok": False,
                "status": status,
                "error": "Invalid JSON-RPC response",
                "result": None,
            }

        if data.get("error"):
            return {
                "ok": False,
                "status": status,
                "error": f"JSON-RPC error: {data['error']}",
                "result": None,
            }

        return {
            "ok": True,
            "status": status,
            "error": None,
            "result": data.get("result"),
        }

    except requests.Timeout:
        return {
            "ok": False,
            "status": None,
            "error": "TIMEOUT",
            "result": None,
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": None,
            "error": type(exc).__name__,
            "result": None,
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": type(exc).__name__,
            "result": None,
        }


def check_solana(name, url, required=False):
    if not configured(url):
        return {
            "name": name,
            "ok": not required,
            "configured": False,
            "status": None,
            "detail": "NOT CONFIGURED",
        }

    result = post_jsonrpc(url, "getSlot")

    if result["ok"]:
        return {
            "name": name,
            "ok": True,
            "configured": True,
            "status": result["status"],
            "detail": f"HTTP {result['status']} | getSlot OK",
        }

    return {
        "name": name,
        "ok": False,
        "configured": True,
        "status": result["status"],
        "detail": (
            f"HTTP {result['status']} | {result['error']}"
            if result["status"]
            else result["error"]
        ),
    }


def check_evm(name, url, required=True):
    if not configured(url):
        return {
            "name": name,
            "ok": not required,
            "configured": False,
            "status": None,
            "detail": "NOT CONFIGURED",
        }

    result = post_jsonrpc(url, "eth_chainId")

    if result["ok"]:
        chain_id = result["result"]

        return {
            "name": name,
            "ok": True,
            "configured": True,
            "status": result["status"],
            "detail": (
                f"HTTP {result['status']} | "
                f"eth_chainId OK | chain_id={chain_id}"
            ),
        }

    return {
        "name": name,
        "ok": False,
        "configured": True,
        "status": result["status"],
        "detail": (
            f"HTTP {result['status']} | {result['error']}"
            if result["status"]
            else result["error"]
        ),
    }


def check_http(name, url, required=True):
    if not configured(url):
        return {
            "name": name,
            "ok": not required,
            "configured": False,
            "status": None,
            "detail": "NOT CONFIGURED",
        }

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "User-Agent": "MASFOX-HealthCheck/10.4",
            },
        )

        ok = 200 <= response.status_code < 300

        return {
            "name": name,
            "ok": ok,
            "configured": True,
            "status": response.status_code,
            "detail": f"HTTP {response.status_code}",
        }

    except requests.Timeout:
        return {
            "name": name,
            "ok": False,
            "configured": True,
            "status": None,
            "detail": "TIMEOUT",
        }

    except requests.RequestException as exc:
        return {
            "name": name,
            "ok": False,
            "configured": True,
            "status": None,
            "detail": type(exc).__name__,
        }

    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "configured": True,
            "status": None,
            "detail": type(exc).__name__,
        }


def print_result(result):
    if not result["configured"]:
        icon = "⚪"
    elif result["ok"]:
        icon = "🟢"
    else:
        icon = "🔴"

    print(f"{icon} {result['name']}: {result['detail']}")


def main():
    print("=" * 58)
    print("🩺 MASFOX — V10 API / RPC HEALTH CHECK")
    print("=" * 58)

    results = []

    # ---------------------------------------------------------
    # FluxRPC
    # ---------------------------------------------------------
    flux_url = rpc_url_with_flux_key()

    if flux_url:
        flux_result = check_solana(
            "FluxRPC",
            flux_url,
            required=True,
        )
    else:
        flux_result = {
            "name": "FluxRPC",
            "ok": False,
            "configured": False,
            "status": None,
            "detail": "NOT CONFIGURED",
        }

    results.append(flux_result)
    print_result(flux_result)

    # ---------------------------------------------------------
    # Solana RPCs
    # ---------------------------------------------------------
    results.append(
        check_solana(
            "SOLANA_RPC_URL",
            getattr(config, "SOLANA_RPC_URL", ""),
            required=True,
        )
    )

    results.append(
        check_solana(
            "SOLANA_RPC_URL_2",
            getattr(config, "SOLANA_RPC_URL_2", ""),
            required=False,
        )
    )

    results.append(
        check_solana(
            "SOLANA_RPC_URL_3",
            getattr(config, "SOLANA_RPC_URL_3", ""),
            required=False,
        )
    )

    # ---------------------------------------------------------
    # External HTTP APIs
    # ---------------------------------------------------------
    dexscreener_url = (
        "https://api.dexscreener.com/latest/dex/search"
        "?q=SOL"
    )

    results.append(
        check_http(
            "DexScreener",
            dexscreener_url,
            required=True,
        )
    )

    birdeye_url = "https://public-api.birdeye.so/"

    results.append(
        check_http(
            "Birdeye",
            birdeye_url,
            required=True,
        )
    )

    rugcheck_url = "https://api.rugcheck.xyz/v1/stats/overview"

    results.append(
        check_http(
            "RugCheck",
            rugcheck_url,
            required=True,
        )
    )

    # ---------------------------------------------------------
    # Helius
    # ---------------------------------------------------------
    helius_key = str(
        getattr(config, "HELIUS_API_KEY", "") or ""
    ).strip()

    if helius_key:
        helius_url = (
            "https://mainnet.helius-rpc.com/"
            f"?api-key={helius_key}"
        )

        helius_result = check_solana(
            "Helius",
            helius_url,
            required=True,
        )
    else:
        helius_result = {
            "name": "Helius",
            "ok": False,
            "configured": False,
            "status": None,
            "detail": "NOT CONFIGURED",
        }

    results.append(helius_result)

    # ---------------------------------------------------------
    # EVM RPCs
    # ---------------------------------------------------------
    results.append(
        check_evm(
            "BASE_RPC_URL",
            getattr(config, "BASE_RPC_URL", ""),
            required=True,
        )
    )

    results.append(
        check_evm(
            "BASE_RPC_URL_2",
            getattr(config, "BASE_RPC_URL_2", ""),
            required=False,
        )
    )

    results.append(
        check_evm(
            "ROBINHOOD_RPC_URL",
            getattr(config, "ROBINHOOD_RPC_URL", ""),
            required=True,
        )
    )

    results.append(
        check_evm(
            "ARC_RPC_URL",
            getattr(config, "ARC_RPC_URL", ""),
            required=True,
        )
    )

    # Print remaining results after FluxRPC.
    for result in results[1:]:
        print_result(result)

    # ---------------------------------------------------------
    # Safe configuration summary
    # ---------------------------------------------------------
    print()
    print("=" * 58)
    print("⚙️ CONFIGURATION")
    print("=" * 58)

    print(
        "AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN =",
        getattr(config, "AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN", "N/A"),
    )

    print(
        "AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN =",
        getattr(config, "AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN", "N/A"),
    )

    print(
        "AUTO_SIGNAL_MIN_SCORE =",
        getattr(config, "AUTO_SIGNAL_MIN_SCORE", "N/A"),
    )

    print(
        "AUTO_SIGNAL_MIN_RECOMMENDATION =",
        getattr(config, "AUTO_SIGNAL_MIN_RECOMMENDATION", "N/A"),
    )

    print(
        "AUTO_SIGNAL_MIN_SECURITY =",
        getattr(config, "AUTO_SIGNAL_MIN_SECURITY", "N/A"),
    )

    print(
        "MIN_MARKETCAP =",
        getattr(config, "MIN_MARKETCAP", "N/A"),
    )

    print(
        "MAX_MARKETCAP =",
        getattr(config, "MAX_MARKETCAP", "N/A"),
    )

    # ---------------------------------------------------------
    # Secret-safe environment status
    # ---------------------------------------------------------
    print()
    print("=" * 58)
    print("🔐 SECRET STATUS")
    print("=" * 58)

    print(
        "HELIUS_API_KEY:",
        "SET" if configured(getattr(config, "HELIUS_API_KEY", "")) else "MISSING",
    )

    print(
        "BIRDEYE_API_KEY:",
        "SET" if configured(getattr(config, "BIRDEYE_API_KEY", "")) else "MISSING",
    )

    print(
        "FLUXRPC_API_KEY:",
        "SET" if configured(getattr(config, "FLUXRPC_API_KEY", "")) else "MISSING",
    )

    print(
        "BOT_TOKEN:",
        "SET" if configured(getattr(config, "BOT_TOKEN", "")) else "MISSING",
    )

    print(
        "AUTO_SIGNAL_CHAT_ID:",
        "SET"
        if configured(getattr(config, "AUTO_SIGNAL_CHAT_ID", ""))
        else "MISSING",
    )

    print(
        "GROUP_ID:",
        "SET" if configured(getattr(config, "GROUP_ID", "")) else "MISSING",
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------
    print()
    print("=" * 58)
    print("📊 SUMMARY")
    print("=" * 58)

    critical_failures = []
    optional_failures = []

    for result in results:
        if result["ok"]:
            print(f"🟢 {result['name']}")
        elif not result["configured"]:
            if result["name"] in {
                "SOLANA_RPC_URL_2",
                "SOLANA_RPC_URL_3",
            }:
                print(f"⚪ {result['name']} — NOT CONFIGURED")
            else:
                print(f"🔴 {result['name']} — NOT CONFIGURED")
                if result["name"] not in {
                    "SOLANA_RPC_URL_2",
                    "SOLANA_RPC_URL_3",
                }:
                    critical_failures.append(result["name"])
        else:
            print(f"🔴 {result['name']} — {result['detail']}")

            if result["name"] in {
                "SOLANA_RPC_URL_2",
                "SOLANA_RPC_URL_3",
                "BASE_RPC_URL_2",
            }:
                optional_failures.append(result["name"])
            else:
                critical_failures.append(result["name"])

    print()

    if critical_failures:
        print(
            "⚠️ Critical API/RPC failures:",
            ", ".join(critical_failures),
        )
    else:
        print("🟢 Critical API/RPC checks: PASS")

    if optional_failures:
        print(
            "ℹ️ Optional RPC issues:",
            ", ".join(optional_failures),
        )

    print("=" * 58)

    # Do not fail the shell only because optional RPCs are absent.
    return 1 if critical_failures else 0


if __name__ == "__main__":
    sys.exit(main())
