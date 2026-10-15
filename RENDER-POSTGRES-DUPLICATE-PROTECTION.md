# Render PostgreSQL: persistent signal history

This update changes `services/history.py` to use PostgreSQL when `DATABASE_URL`
starts with `postgres://` or `postgresql://`, while keeping SQLite for local use.
It adds `psycopg[binary]` to requirements.

## Render setup
1. Create a Render **Postgres** database in the same region as the bot service.
2. Open the database page and copy its **Internal Database URL** privately.
3. In the Render service that runs `python bot.py` (the worker), open **Environment**.
4. Add/update `DATABASE_URL` with that Internal Database URL. Do not commit it to GitHub or share it in chat.
5. Save changes and redeploy the worker.

The signal history table is created automatically. This protects the bot's recorded
signal history across restarts/redeploys, provided the running bot service has this
`DATABASE_URL` set. Local SQLite remains the default if no PostgreSQL URL is set.

Note: the existing PNL tracker and dashboard report still use their existing local
SQLite handling; this update makes the auto-signal history PostgreSQL-backed.
