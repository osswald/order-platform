# Vendiqo Cloud

The cloud stack is the central admin and API for Vendiqo: multi-tenant back office for **Verleiher** (hire companies) who rent POS hardware to event customers. It configures organisations and events, serves reports, and exposes the edge API that on-venue Pis sync against.

**Stack:** FastAPI + PostgreSQL (backend), Vue 3 / Vite / TypeScript (admin UI).

## What Vendiqo Cloud does

### Multi-tenancy and roles

Each **Verleiher** (`hire_companies`) owns customer organisations, appliances, and lendings.

| Role | Scope |
|------|-------|
| `platform_admin` | Manage Verleiher; operational UI requires an active Verleiher + header `X-Hire-Company-Id` |
| `tenant_admin` | Full admin within one Verleiher (organisations, appliances, users, lendings) |
| `organisation_admin` | Manage assigned organisation(s) |
| `member` | Event customer users within assigned organisations |

On startup, `apply_schema_patches()` creates a default Verleiher named **Vendiqo** (override with `DEFAULT_HIRE_COMPANY_NAME`). Platform admins pick **Aktiver Verleiher** in the sidebar; route `/verleiher` manages Verleiher (platform admin only).

### Event management

- Lifecycle: config → test → prod → archive
- Payment modes: `instant`, `pay_now`, `pay_later`
- Payment types: cash, TWINT, SumUp, Stripe Terminal
- Per-event configuration: stations, printer rules, app layouts, waiters (PINs), cash registers, vouchers, kitchen monitor printers, receipt printing (logos, fonts, footers)

### Master data

Articles, categories, ingredients, waiters, organisations, tax codes, countries, payment types. Orderjutsu import wizard at `/events/import/orderjutsu`.

### Hardware

Appliance types: server, printer, mobile, tablet, router, ap. Server appliances get Pi pairing codes; printer appliances store IPv4 and ESC/POS feed lines. **Lendings** date-bound appliance rentals — required for edge sync.

### Reporting and exports

Sales reports, event stats, transactions, cash sessions, payment batches, bookkeeping export, collective bill PDF download.

### Payments (Stripe)

Stripe Connect onboarding per organisation (`/settings/stripe/*`). Stripe Terminal edge API for card payments on Android devices. Stripe keys are optional for local dev — core POS works without them.

See [docs/stripe-connect-terminal.md](../docs/stripe-connect-terminal.md).

### Edge API

Authenticated bundle and operational sync for paired Pis (`X-Edge-Client-Id` / `X-Edge-Secret`): pairing, bundle pull, operational snapshot/chunk sync.

### Hosted Cloud-Pi

Temporary browser Pis for events in **config** status (see [Hosted Cloud-Pi](#hosted-cloud-pi-config-events) below).

### Locales

Admin UI in German and English. Money and dates formatted per UI locale and organisation country code (Babel backend, vue-i18n frontend).

---

## Production deployment

Production stack: **Caddy** (HTTPS) → **nginx** (admin SPA) + **FastAPI/gunicorn** (API) → **PostgreSQL**.

Local development uses `docker compose up` with the dev Dockerfiles (Vite dev server + uvicorn).

## Local development

```bash
cd cloud
cp .env.example .env
# Set local dev values (see comments in .env.example), then:
docker compose up --build
```

- API: `http://localhost:8000` (health: `/health`)
- Admin UI: `http://localhost:5173`

Suggested dev settings in `.env`:

| Variable | Local value |
|----------|-------------|
| `POSTGRES_USER` | `cloud` |
| `POSTGRES_PASSWORD` | `devpass123` |
| `POSTGRES_DB` | `cloud` |
| `SECRET_KEY` | `devsecretkey123456789` |
| `ADMIN_EMAIL` | `admin@vendiqo.local` |
| `ADMIN_PASSWORD` | `admin123` |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:5174` |
| `REFRESH_COOKIE_SECURE` | `false` |
| `ENABLE_OPENAPI` | `true` |

Postgres credentials are written into the Docker volume **only on first init**. If you change `POSTGRES_USER` or `POSTGRES_PASSWORD` later, reset the local volume (this deletes local DB data):

```bash
docker compose down -v
docker compose up --build
```

Do **not** run `docker compose down -v` on production.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production compose (Caddy, no public DB/backend ports) |
| `Caddyfile` | TLS + reverse proxy for `vendiqo.ch`, `admin.vendiqo.ch`, and `api.vendiqo.ch` |
| `../website/Dockerfile.prod` | Multi-stage build → nginx static site (landing + Datenschutz) |
| `.env.example` | Template for production secrets and settings |
| `frontend/Dockerfile.prod` | Multi-stage build → nginx static SPA |
| `backend/Dockerfile.prod` | gunicorn + uvicorn workers |

## VPS prerequisites

- Ubuntu/Debian VPS with Docker Engine and Docker Compose plugin
- DNS A records pointing to the VPS (TTL can be 3600):
  - `vendiqo.ch` → server IP
  - `www.vendiqo.ch` → server IP
  - `admin.vendiqo.ch` → server IP
  - `api.vendiqo.ch` → server IP
  - `*.demo.vendiqo.ch` → server IP (wildcard for hosted Cloud-Pi sandboxes)
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

curl -I https://www.vendiqo.ch/datenschutz/
# HTTP/2 200
```

Public privacy policy (e.g. Google Play Console): `https://www.vendiqo.ch/datenschutz/` (`https://vendiqo.ch/datenschutz/` also works).

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

## Hosted Cloud-Pi (config events)

Organisation users can start a temporary browser Pi from the event admin UI while an event is in **Konfiguration** status.

- Set `HOSTED_PI_MANAGER_SECRET` in `.env` (same value for `cloud-backend` and `hosted-pi-manager`).
- DNS wildcard: `*.demo.vendiqo.ch` → VPS IP (see prerequisites above).
- Pi images: CI builds `linux/amd64,linux/arm64`; hosted instances use the amd64 tags on the VPS.
- Max **5** concurrent instances globally; each runs up to **24 hours** with emulated printers.

### Pi image updates (layout, receipts, etc.)

Hosted sandboxes do **not** use the cloud admin build. Each instance pulls pre-built Pi images from GHCR (`PI_BACKEND_IMAGE` / `PI_FRONTEND_IMAGE` in `.env`, default `ghcr.io/.../pi-*-amd64-latest`).

After changing `pi/backend` or `pi/frontend`:

1. Push to `main` — the **Pi Docker images** workflow (`.github/workflows/pi-docker.yml`) builds and pushes new `pi-backend-amd64-latest` and `pi-frontend-amd64-latest` tags.
2. Confirm the workflow succeeded on GitHub Actions.
3. On the VPS, rebuild the orchestrator (needed after `hosted-pi-manager` code changes): `docker compose -f docker-compose.prod.yml up -d --build hosted-pi-manager cloud-backend cloud-frontend`
4. **Stop and restart** each hosted Cloud-Pi from the admin UI. New instances pull fresh images from GHCR (`pull_policy: always`).

Rebuilding `cloud-frontend` alone does not update the Pi app inside hosted sandboxes.

**Stale Pi images on the VPS:** `docker compose up` reuses locally cached `:latest` images unless forced to pull. If a restarted sandbox still shows old behaviour, on the VPS run:

```bash
docker pull ghcr.io/osswald/order-platform:pi-frontend-amd64-latest
docker pull ghcr.io/osswald/order-platform:pi-backend-amd64-latest
```

Then start a new Cloud-Pi from the admin UI. If pulls fail with “denied”, log in to GHCR on the VPS (`docker login ghcr.io`) with a token that has `read:packages`.

Verify the running image digest:

```bash
docker image inspect ghcr.io/osswald/order-platform:pi-frontend-amd64-latest --format '{{.Id}} {{.Created}}'
```

## Troubleshooting

- **502 from Caddy**: check `docker compose -f docker-compose.prod.yml logs cloud-backend cloud-frontend`
- **Certificate errors**: confirm DNS A records and that ports 80/443 reach the VPS
- **CORS errors**: `ALLOWED_ORIGINS` must include `https://admin.vendiqo.ch` (no trailing slash)
- **Login cookie not set**: ensure `REFRESH_COOKIE_SECURE=true` in production
