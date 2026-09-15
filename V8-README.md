# SALIM SAUKI DATA V8 — Multi-Language Foundation

V8 keeps the existing Python Telegram/DEX engine intact and adds TypeScript as a separate API/dashboard layer.

## Languages

- Python: Telegram bot, scanner, security, AI/scoring and existing services.
- TypeScript/Node.js: V8 API gateway and future real-time services.
- HTML/CSS: dashboard presentation.

## Important architecture rule

TypeScript does **not** replace the Python engine in V8. It communicates with the existing Python dashboard API so the proven Solana/Base logic remains unchanged.

## Start order

1. Start the existing Python dashboard on port 8000.
2. Start the V8 TypeScript API on port 8787.
3. The V8 dashboard/frontend can call `/api/v8/*` without touching scanner internals.

## Termux setup

```bash
pkg install nodejs
cd ~/SALIM-SAUKI-DATA-V8-TEST/api/typescript
npm install
npm run build
npm start
```

## V8 API

- `/api/v8/health`
- `/api/v8/dashboard/health`
- `/api/v8/scan?query=sol`
- `/api/v8/scan?query=base`

The Python dashboard must expose the corresponding `/health` and `/api/scan` routes. If a route is unavailable, V8 reports the upstream error instead of fabricating data.
