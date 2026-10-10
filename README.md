# MASFOX — V10 Multi-Chain DEX Analysis Bot

MASFOX is a Telegram-based multi-chain token-analysis system. It combines DexScreener discovery, market filters, AI/GEM scoring, security analysis, final-signal validation, Telegram delivery, PNL tracking, group cleanup, API health checks, and a web dashboard.

> ⚠️ This software provides automated market/security analysis. It is not financial advice and does not guarantee profit or token safety.

## Supported chains

- 🟣 Solana
- 🔵 Base / EVM
- 🟢 Robinhood Chain
- 🟠 Arc

## Core pipeline

```text
DexScreener discovery
        ↓
Best-pool selection
        ↓
Chain-aware market filters
        ↓
AI scoring + GEM detection
        ↓
Security analysis
        ↓
Final Signal Engine
        ↓
Recommendation / ranking
        ↓
Auto Signal Engine
        ↓
Telegram GEM RADAR message
```

## Signal delivery

Telegram Auto Signal sends only the final approved signal classes:

```text
🔥 STRONG GEM  → SEND
🚀 GEM SIGNAL  → SEND
👀 EARLY GEM   → SEND
🟡 WATCH       → NOT SENT
⛔ NO SIGNAL   → NOT SENT
```

Final-signal and security gates remain authoritative. A high AI/GEM score alone does not create an auto signal.

## Signal quota

The default quota is **8 signals per scan**, with a maximum of **2 per supported chain**:

- Solana: up to 2
- Base: up to 2
- Robinhood: up to 2
- Arc: up to 2

The global limit and per-chain limit are configurable through `.env`.

## Market-cap requirement

The production scanner keeps the requested market-cap range:

```text
MIN_MARKETCAP = $10,000
MAX_MARKETCAP = $1,000,000
```

The project also keeps separate chain-aware discovery thresholds and final-signal quality/security gates. These should not be weakened merely to manufacture signals.

## Security

### Solana

The security pipeline checks token/account state, initialization, mint/freeze authority risk, RPC-derived information, and configured security thresholds.

### Base / EVM

The security pipeline performs address and contract validation, metadata checks, honeypot/risk simulation when enabled, tax/risk checks, and other available contract-risk signals.

### Other supported chains

Robinhood Chain and Arc use chain-aware discovery and security handling. Unsupported or invalid chain/token data is rejected instead of being turned into a positive signal.

## Telegram commands

- `/start`
- `/scan solana`
- `/scan base`
- `/scan robinhood`
- `/scan arc`
- `/scan <query>`
- `/analyze <query>`
- `/analyze <contract>`
- `/help`
- `/status`
- `/health`
- `/pnl`
- `/autostatus`

## GEM RADAR message

Auto signals use the premium `MASFOX || GEM RADAR` format. Messages include real token/market data when available, AI/GEM/security/final scores, signal classification, contract and available external links.

The formatter avoids claiming unsupported facts such as liquidity being locked unless the underlying data actually confirms it.

## Dashboard

The Render web service exposes:

- `/` — production status page
- `/dashboard` — full multi-chain scanner dashboard
- `/health` — Render health check
- `/api/health` — dashboard/API health
- `/api/status` — bot status JSON
- `/api/scan?q=sol` — scanner JSON endpoint (rate-limited)

The dashboard is served from the same Flask web service as the Telegram bot, so a normal single Render web service does not need a second Python web process just to expose the dashboard.

## Render deployment

`render.yaml` is included for the standard Render web-service deployment:

```text
Build:  pip install -r requirements.txt
Start: python bot.py
Health: /health
```

Set the real secrets/API keys in Render Environment Variables. `BOT_USERNAME` is optional and is used only to build the Telegram dashboard link. Do not commit `.env` or paste live secrets into source control.

### Important Render note

The bot uses SQLite by default for local history/cleanup data. A normal Render filesystem is not a substitute for durable production storage. If persistent PNL/history/cleanup state is required across redeploys, use a durable storage strategy appropriate to the application rather than assuming the container filesystem is permanent.

## Environment template

Use `.env.example` as the safe template. It contains variable names only and must never contain real credentials.

Important values include:

```env
AUTO_SIGNAL_ENABLED=true
AUTO_SIGNAL_INTERVAL=60
AUTO_SIGNAL_MAX_SIGNALS_PER_SCAN=8
AUTO_SIGNAL_MAX_SIGNALS_PER_CHAIN=2

MIN_MARKETCAP=10000
MAX_MARKETCAP=1000000
MIN_SECURITY_SCORE=69

BASE_HONEYPOT_ENABLED=true
BASE_HONEYPOT_REQUIRED=true
```

## Group auto-cleanup

The cleanup service can delete configured group messages after the configured delay. Example settings:

```env
CLEANUP_BOT_TOKEN=YOUR_CLEANUP_BOT_TOKEN
CLEANUP_CHAT_ID=YOUR_TELEGRAM_GROUP_CHAT_ID
CLEANUP_DELETE_AFTER_SECONDS=300
CLEANUP_CHECK_INTERVAL=15
CLEANUP_DATABASE_PATH=./cleanup_messages.db
```

If the cleanup token equals the main bot token, cleanup is attached to the main Telegram application instead of starting a second polling process. This avoids Telegram `409 Conflict` caused by two `getUpdates` consumers using the same bot token.

## Project structure

```text
SALIM-SAUKI-DATA/
├── ai/
├── handlers/
├── services/
├── static/
├── templates/
├── tests/
├── web/
├── dashboard/
├── api/
├── bot.py
├── config.py
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

Development backup files may exist beside active modules. They are recovery copies and are not imported by the running application.

## TypeScript V8 layer

The TypeScript API/dashboard layer remains additive. It does not replace the trusted Python scanner/security engine.

The API can be built from:

```bash
cd api/typescript
npm install
npm run build
```

Its upstream Python dashboard URL is configurable through `PYTHON_DASHBOARD_URL`.

## API health

`check_apis.py` performs safe API health checks without printing API keys. The production health command covers configured RPC/API services such as FluxRPC, Solana RPCs, Base RPCs, DexScreener, RugCheck, Birdeye, and Helius when credentials are configured.

## Testing

Run:

```bash
python -m compileall -q .
pytest -q
```

The current uploaded build passes the existing Python test suite before the dashboard/deployment cleanup, and the corrected build is re-tested after changes.

## Git / secrets

Never commit:

- `.env`
- live API keys
- Telegram bot tokens
- live SQLite databases
- database WAL/SHM files
- Python cache files

The repository `.gitignore` is configured to exclude these classes of files.
