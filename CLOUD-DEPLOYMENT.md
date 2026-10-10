# MASFOX — Cloud-Agnostic Deployment

The application is designed to run as one portable Python container. It does not require Render-specific APIs.

## Supported deployment styles

- Render
- Oracle Cloud VM
- AWS EC2 / Lightsail
- Google Cloud VM
- Azure VM
- DigitalOcean
- Any Linux VPS
- Local Docker
- Termux for development/testing

## Required environment

Copy `.env.example` to `.env` and set the real secrets in the deployment platform's secret/environment manager. Never commit `.env`.

## Docker

```bash
docker compose up -d --build
```

The terminal is available on port `10000` by default.

## Cloud port

Set `PORT` to the port supplied by the cloud provider. The application listens on `0.0.0.0`.

## Persistent storage

SQLite is supported when the platform provides a persistent disk/volume. The important files are:

- `salim_sauki_data.db`
- `cleanup_messages.db`

For multi-instance/high-availability deployments, use a managed PostgreSQL database and adapt the persistence layer before running multiple application replicas. Do not run multiple SQLite replicas against the same file.

## Health endpoints

- `/health` — simple liveness
- `/ready` — readiness
- `/api/health` — dashboard API health
- `/api/status` — runtime status
- `/api/signals` — recently delivered signal feed
- `/api/signals/<chain>/<address>` — signal detail

## Live terminal

- `/` — primary live GEM terminal
- `/dashboard` — live GEM terminal alias
- `/status` — legacy runtime/status page

## Signal source

The web terminal reads the same persistent signal history used by the Auto Signal Engine. A signal appears on the web feed only after the Telegram delivery succeeds. This prevents the website from showing signals that the bot failed to deliver.
