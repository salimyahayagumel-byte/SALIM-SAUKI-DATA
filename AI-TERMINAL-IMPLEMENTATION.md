# SALIM SAUKI DATA — AI Terminal UI

This update adds a responsive AI Terminal interface to the existing dashboard and renames visible dashboard branding from MASFOX to SALIM SAUKI DATA.

## Available terminal commands
- `/help`: command guide
- `/signals`: summarizes saved/delivered signals from `/api/signals`
- `/top`: shows the highest available final-score signals
- `/scan`: calls the existing `/api/scan` endpoint
- `/security`: opens contract lookup and explains that security needs live contract data
- `/pnl`: opens the existing PNL view
- `/search`: opens contract-address lookup
- `/status`: checks `/api/health`

## Important scope note
The terminal's explanations are rule-based and use the dashboard's connected data. This update does not add a third-party LLM provider, does not invent token data, and does not execute trades. A true generative AI provider can be integrated later through a server-side endpoint with secrets kept server-side.

## Files changed
- `templates/dashboard.html`
- `static/css/style.css`
- `static/js/dashboard.js`

Existing scanner, Telegram bot, PNL tracking, security scoring, environment files, and databases are otherwise unchanged.
