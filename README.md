# Farmers-Market Ops Lite

A minimal, self-hostable scaffold for a farmers market operations toolkit. It bundles a FastAPI backend, offline-ready PWA shell, and optional integrations for routing and SMS notifications.

## Project layout

```
.
├── docker-compose.yml
├── Caddyfile
└── app/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── db.py
    ├── models.py
    ├── schemas.py
    ├── utils.py
    ├── .env.example
    └── static/
        ├── index.html
        ├── manifest.webmanifest
        └── sw.js
```

## Quick start

1. Review the default environment configuration in `app/.env` (copy of the example file) and adjust it for your deployment.

2. Build and start the stack using the helper script (falls back to copying `.env.example` if `app/.env` is missing):

   ```bash
   ./scripts/bootstrap.sh
   ```

   The script verifies that Docker and the Compose plugin are available, attempts to install them automatically on Debian/Ubuntu systems (using `apt-get` with sudo when necessary), and then runs `docker compose up --build`. The FastAPI app is exposed internally on port 8000 and served publicly through Caddy with automatic HTTPS (when `DOMAIN` is not `localhost`).

   > **Note:** If Docker is installed during this process, you may need to log out and back in (or re-run the script with sudo) so your user gains access to the `docker` group.

3. Visit the app in your browser at `https://<DOMAIN>` (or `http://localhost` for local development).

## Notes

- Data is stored in a SQLite database within the `app_data` Docker volume.
- Optional integrations:
  - Configure `OSRM_URL` to enable driving-route requests against an external OSRM server.
  - Set the Twilio credentials (`TWILIO_*`) to allow sending pickup notifications via SMS.
- The static frontend is a lightweight offline-first shell that queues API writes when offline and replays them once connectivity is restored.
