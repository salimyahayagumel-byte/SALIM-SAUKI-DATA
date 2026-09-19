import asyncio
import httpx

from telegram import Update
from telegram.ext import ContextTypes

from config import (
    FLUXRPC_RPC_URL,
    SOLANA_RPC_URL,
    SOLANA_RPC_URL_2,
    SOLANA_RPC_URL_3,
    BASE_RPC_URL,
    BASE_RPC_URL_2,
    BIRDEYE_API_KEY,
    HELIUS_API_KEY,
)
from services.scanner import TokenScanner


async def _rpc(url, method, params=None, timeout=8):
    if not url:
        return False, "NOT CONFIGURED"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("error"):
                return False, "RPC ERROR"
            if data.get("jsonrpc") != "2.0":
                return False, "INVALID RPC RESPONSE"
            return True, "OK"
    except Exception as exc:
        return False, type(exc).__name__


async def _http(url, headers=None, params=None, timeout=8):
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return True, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, type(exc).__name__


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    scanner = TokenScanner()

    # Test all critical providers concurrently. Secrets are never printed.
    solana = [
        ("FluxRPC", FLUXRPC_RPC_URL),
        ("Solana RPC 1", SOLANA_RPC_URL),
        ("Solana RPC 2", SOLANA_RPC_URL_2),
        ("Solana RPC 3", SOLANA_RPC_URL_3),
    ]
    base = [
        ("Base RPC 1", BASE_RPC_URL),
        ("Base RPC 2", BASE_RPC_URL_2),
    ]

    tasks = []
    names = []

    for name, url in solana:
        names.append(name)
        tasks.append(_rpc(url, "getHealth"))

    for name, url in base:
        names.append(name)
        tasks.append(_rpc(url, "eth_blockNumber"))

    names.append("DexScreener")
    tasks.append(_http(
        "https://api.dexscreener.com/latest/dex/search",
        params={"q": "SOL"},
    ))

    names.append("RugCheck")
    tasks.append(_http(
        "https://api.rugcheck.xyz/v1/stats/new_tokens",
    ))

    if BIRDEYE_API_KEY:
        names.append("Birdeye")
        tasks.append(_http(
            "https://public-api.birdeye.so/defi/price",
            headers={
                "X-API-KEY": BIRDEYE_API_KEY,
                "Accept": "application/json",
                "x-chain": "solana",
            },
            params={
                "address": "So11111111111111111111111111111111111111112",
            },
        ))

    if HELIUS_API_KEY:
        names.append("Helius")
        tasks.append(_rpc(
            f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}",
            "getHealth",
        ))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    lines = [
        "🩺 SALIM SAUKI DATA — API HEALTH",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for name, result in zip(names, results):
        if isinstance(result, Exception):
            ok, detail = False, type(result).__name__
        else:
            ok, detail = result

        lines.append(
            f"{'🟢' if ok else '🔴'} {name}: {detail}"
        )

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━",
        "🔐 Secrets hidden",
        "🛡️ Solana fallback: FluxRPC + configured RPCs",
        "🔵 Base fallback: configured RPCs",
    ])

    await update.message.reply_text("\n".join(lines))
