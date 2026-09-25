# SALIM SAUKI DATA — V8.8 Relaxed Signals

This build keeps the market-cap range unchanged while relaxing several signal gates to discover more candidates. See `V8.8-CHANGELOG.md`.

# SALIM SAUKI DATA — DEX Analysis Bot

Professional multi-chain Telegram token-analysis bot focused on **Solana** and **Base**.

> ⚠️ This project provides automated market/security analysis. It is not financial advice and does not guarantee profit or token safety.

## Core pipeline

```text
DexScreener discovery
        ↓
Best-pool selection per token
        ↓
Market filters
        ↓
AI scoring + GEM detection
        ↓
Chain-aware security
        ↓
Final Signal Engine
        ↓
Recommendation Engine
        ↓
Smart ranking
        ↓
Telegram Auto Signal
```

## Supported chains

- 🟣 Solana
- 🔵 Base / EVM (chain ID 8453)

## Main features

- AI token scoring
- GEM / early-GEM detection
- Liquidity and volume analysis
- Buy/sell ratio analysis
- Final signal engine
- Recommendation engine
- Security checks
- Solana mint/freeze authority checks
- Base contract validation
- Base Honeypot.is buy/sell simulation and risk analysis
- Base tax / proxy / source-code risk signals when supplied by the security API
- DexScreener discovery
- Solana + Base chain-aware token tools
- Duplicate protection
- Signal cooldown protection
- Multi-chain fair signal delivery
- Telegram auto alerts
- Professional HTML-formatted Telegram GEM cards with token images when available
- X/Twitter, Telegram and website social enrichment
- Web dashboard

## Telegram commands

- `/start` — start/help message
- `/scan solana` — scan Solana candidates
- `/scan base` — scan Base candidates
- `/scan <query>` — search/analyze a discovery query
- `/analyze <query>` — detailed analysis of the best matching candidate
- `/analyze <contract>` — exact contract lookup when a Solana or EVM address is supplied

## Group Auto-Cleanup Bot

V8.3 includes a second Telegram bot service that runs together with the main DEX bot. It watches one configured group/supergroup and schedules each received message for automatic deletion after **5 minutes**.

### Cleanup settings

Add these values to `.env` (never commit `.env`):

```env
CLEANUP_BOT_TOKEN=YOUR_CLEANUP_BOT_TOKEN
CLEANUP_CHAT_ID=YOUR_TELEGRAM_GROUP_CHAT_ID
CLEANUP_DELETE_AFTER_SECONDS=300
CLEANUP_CHECK_INTERVAL=15
CLEANUP_DATABASE_PATH=./cleanup_messages.db
```

`300` seconds = **5 minutes**. The cleanup queue is stored in SQLite so pending deletions can survive a bot restart.

### Telegram permission

Add the cleanup bot to the target group/supergroup and make it an administrator with **Delete Messages** permission. Keep `CLEANUP_CHAT_ID` set to the intended group so the cleanup service does not target other groups.

### Start both bots

The main DEX analysis bot and the group cleanup bot are started from the same entry point:

```bash
python bot.py
```

When the cleanup credentials are present, the startup log shows `🧹 Cleanup Bot is ACTIVE` and reports the 300-second deletion delay.

## Auto Signal policy

```text
🔥 STRONG GEM  → SEND
🚀 GEM SIGNAL  → SEND
👀 EARLY GEM   → MONITOR ONLY
🟡 WATCH       → MONITOR ONLY
⛔ NO SIGNAL   → IGNORE
```

The default auto-signal limit is **3 messages per scan**, with a maximum of **2 signals per chain** before remaining slots are filled by the best candidates globally. This prevents one chain from starving the other.

## Security model

### Solana

The existing Solana security pipeline checks token/mint account data, initialization and authority-related risk according to the configured thresholds.

### Base

The Base pipeline performs:

1. EVM address validation
2. Contract bytecode validation
3. ERC-20 metadata checks
4. Total-supply/decimals checks
5. Honeypot.is risk/simulation checks when enabled
6. Honeypot detection
7. Buy/sell tax checks
8. Source-code/proxy risk signals when available

The Base Honeypot layer is configurable. When `BASE_HONEYPOT_REQUIRED=true`, the bot fails closed if the external Honeypot check cannot be obtained.

## Configuration highlights

Important `.env` settings include:

```env
AUTO_SIGNAL_ENABLED=true
AUTO_SIGNAL_INTERVAL=60
AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN=3
AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN=2

BASE_RPC_URL=https://mainnet.base.org
BASE_RPC_URL_2=https://base-rpc.publicnode.com
BASE_HONEYPOT_ENABLED=true
BASE_HONEYPOT_REQUIRED=true
BASE_HONEYPOT_TIMEOUT=15
BASE_HONEYPOT_CACHE_SECONDS=300
```

Never commit `.env` or live API keys. Use `.env.example` as the template.

## Project structure

```text
SALIM-SAUKI-DATA/
├── ai/
├── handlers/
├── services/
│   ├── auto_signal.py
│   ├── dexscreener.py
│   ├── final_signal.py
│   ├── scanner.py
│   └── security.py
├── static/
├── templates/
├── tests/
├── web/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
└── README.md
```

Backup files may exist beside services during development. They are retained intentionally as recovery points.

Exact-address analysis uses DexScreener token lookup before the normal market/security/scoring pipeline, reducing the chance that a contract query is accidentally treated as a name search.

## Testing

Run the built-in tests:

```bash
python -m unittest discover -s tests -v
```

Run a syntax check:

```bash
python -m compileall -q .
```

## APIs / services

- DexScreener
- BirdEye
- RugCheck
- Solana RPC providers
- Base RPC providers
- Honeypot.is for optional Base honeypot/security simulation

## Author

**Salim Yahaya**

## Final reliability layer

- Persistent SQLite signal history survives bot restarts.
- `/help`, `/status`, and `/health` Telegram commands are available.
- Environment parsing is defensive: malformed numeric values fall back to safe defaults.
- Auto-signal duplicate/cooldown state is restored from SQLite on startup.
- Existing Solana/Base security, fair multi-chain delivery, exact-address lookup, and Honeypot.is checks remain enabled.

The bot is designed to reject uncertain security data rather than manufacture a positive signal. This is an analysis system, not a profit guarantee.

## V8 Multi-Language Foundation

V8 adds an isolated TypeScript/Node.js API and dashboard layer while preserving the existing Python scanner, security, AI scoring, Solana/Base support, and Telegram engine.


## V8.6 API / RPC reliability fixes

V8.6 adds:
- FluxRPC as the preferred Solana RPC when configured.
- FluxRPC can be configured with `FLUXRPC_RPC_URL` or `FLUXRPC_API_KEY`.
- Solana RPC fallback remains enabled.
- Secret-bearing RPC URLs are no longer printed in Solana success/network logs.
- `check_apis.py` provides a safe API health test without printing API keys.
- Auto Signal Engine now prints rejection reasons per scan, making it easier to see whether signals are blocked by final signal, recommendation, security, or score gates.
- Group cleanup retries temporary Telegram deletion failures instead of removing the queued message immediately.
- Cleanup startup performs a Telegram admin/delete-permission diagnostic.
- If `CLEANUP_BOT_TOKEN` equals `BOT_TOKEN`, cleanup is attached to the already-running main bot instead of starting a second polling process, preventing Telegram `409 Conflict` from competing `getUpdates` consumers.
- Separate Telegram HTTP transports are used when the cleanup bot has a different token.


## V10 diagnostics

- `/autostatus` shows live Auto Signal Engine scan/candidate/rejection statistics.
- `/health` now performs live API checks for FluxRPC, Solana RPCs, Base RPCs, DexScreener, RugCheck, Birdeye, and Helius when configured.
- Solana security RPC selection prefers FluxRPC when `FLUXRPC_API_KEY` or `FLUXRPC_RPC_URL` is configured, then uses configured/fallback RPCs.
- RPC failures are cooled down briefly so an unhealthy endpoint is not hammered every scan.
- Secret-bearing RPC query strings are redacted from logs.


## V10 MC/AGE Expansion
- Scanner market-cap range: $10K-$1M across Solana, Base, Robinhood Chain, and Arc.
- Token age window: 1 second to 48 hours across supported chains.
- Security hard-blocks remain unchanged.
