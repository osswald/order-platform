# Cloud production deployment

Production stack: **Caddy** (HTTPS) → **nginx** (admin SPA) + **FastAPI/gunicorn** (API) → **PostgreSQL**.

Local development still uses `docker compose up` with the dev Dockerfiles (Vite dev server + uvicorn).

## Files

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production compose (Caddy, no public DB/backend ports) |
| `Caddyfile` | TLS + reverse proxy for `admin.vendiqo.ch` and `api.vendiqo.ch` |
| `.env.example` | Template for production secrets and settings |
| `frontend/Dockerfile.prod` | Multi-stage build → nginx static SPA |
| `backend/Dockerfile.prod` | gunicorn + uvicorn workers |

## VPS prerequisites

- Ubuntu/Debian VPS with Docker Engine and Docker Compose plugin
- DNS A records pointing to the VPS (TTL can be 3600):
  - `admin.vendiqo.ch` → server IP
  - `api.vendiqo.ch` → server IP
- Firewall: allow **22/tcp**, **80/tcp**, **443/tcp** only

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Optional persistent Postgres data on the host:

```bash
sudo mkdir -p /data/postgres
sudo chown 999:999 /data/postgres   # postgres image UID
```

## Deploy on the VPS

```bash
git clone <repo-url> order-platform
cd order-platform/cloud

cp .env.example .env
# Edit .env: POSTGRES_PASSWORD, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
# Set POSTGRES_DATA_PATH=/data/postgres if using a host bind mount

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy
```

Caddy obtains Let's Encrypt certificates automatically once DNS resolves to this server.

## Smoke tests

```bash
curl -sS https://api.vendiqo.ch/health
# {"status":"ok"}

curl -I https://admin.vendiqo.ch/
# HTTP/2 200
```

Log in at `https://admin.vendiqo.ch` with the bootstrap admin from `.env` (created on first start if no user exists).

## Pi edge configuration

Point the Pi backend at the production API:

```bash
CLOUD_BASE_URL=https://api.vendiqo.ch
```

Re-register appliances / edge credentials against production after cutover.

## Updates

```bash
cd order-platform/cloud
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Backups (recommended)

```bash
docker compose -f docker-compose.prod.yml exec -T cloud-db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup-$(date +%F).sql
```

Store backups off the VPS on a schedule.

## Troubleshooting

- **502 from Caddy**: check `docker compose -f docker-compose.prod.yml logs cloud-backend cloud-frontend`
- **Certificate errors**: confirm DNS A records and that ports 80/443 reach the VPS
- **CORS errors**: `ALLOWED_ORIGINS` must include `https://admin.vendiqo.ch` (no trailing slash)
- **Login cookie not set**: ensure `REFRESH_COOKIE_SECURE=true` in production
