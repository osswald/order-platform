# Raspberry Pi edge server

The Raspberry Pi stack is the on-prem venue server:

- **FastAPI** backend
- **SQLite** local data store
- **Vue PWA** for waiters, registers, pickup screens, and kitchen monitors
- automatic cloud sync through the cloud edge API

The Pi is designed to keep selling while the internet is unavailable. It serves the local PWA and stores orders in SQLite, then pushes them to cloud when connectivity returns.

## Production network and first boot

Production Pis are intended to run headlessly on the Verleiher-supplied router.

```text
Pi URL:  http://192.168.192.10
eth0:    192.168.192.10/24
gateway: 192.168.192.1
dns:     192.168.192.1, 1.1.1.1
```

The static Ethernet config is in:

```text
pi/deploy/networkmanager-vendiqo-eth0.nmconnection
```

On first boot, open the Pi from a device on the same router network:

```text
http://192.168.192.10
```

If the Pi is not paired yet, the PWA redirects to the local setup page.

## Cloud pairing

Pairing is the normal production credential flow.

1. In cloud admin, create or open a **server** appliance.
2. In the server appliance detail, create a Raspberry Pi pairing code.
3. Boot the Pi SD card and open `http://192.168.192.10`.
4. Enter the pairing code on the Pi setup page.
5. The Pi calls cloud `POST /edge/v1/pair`.
6. Cloud creates a new SD-card installation credential for that server appliance.
7. The Pi stores the returned credentials in `/data/edge.env`.

The cloud only returns `EDGE_SECRET` once during pairing. The Pi backend reads credentials from environment variables first and then from `/data/edge.env`.

**Setup lockdown (production):**

- `POST /v1/setup/pair` is rejected with **403** if the Pi is already paired (`/data/edge.env` exists).
- The cloud URL sent in the pairing request is **ignored** unless `ALLOW_CLOUD_URL_OVERRIDE=true`; production uses `DEFAULT_CLOUD_BASE_URL` (default `https://api.vendiqo.ch`).
- `POST /v1/setup/unpair` clears local credentials when `PI_SETUP_UNPAIR_SECRET` is set on the Pi and the request body includes the matching `unpair_secret`.

Local Docker dev enables `ALLOW_CLOUD_URL_OVERRIDE=true` in `docker-compose.yml` so you can point pairing at `http://host.docker.internal:8000`.

## Multiple SD cards per server

A server appliance can have multiple paired SD cards, for example:

```text
Apollo
- Main SD card
- Backup SD card 1
- Backup SD card 2
```

Each SD card gets its own:

- `edge_client_id`
- `edge_secret`
- label/device name
- status (`active` / `revoked`)
- `last_seen_at`

This is safer than cloning one secret because cloud can identify and revoke one broken/lost card without invalidating the others.

Important operating rule:

> Only one SD card for the same server appliance should be powered on at a time.

If the active SD card breaks, insert a paired backup SD card and boot the Pi. It should continue syncing as the same server appliance. In cloud admin, individual SD cards can be revoked from the server appliance detail.

Legacy manual appliance credentials (`EDGE_CLIENT_ID` / `EDGE_SECRET` on the appliance itself) are still accepted for compatibility, but new production setup should use pairing.

## Credential/config files

### Production paired Pi

Stored on the persistent Docker volume:

```text
/data/edge.env
```

Example:

```env
CLOUD_BASE_URL=https://api.vendiqo.ch
EDGE_CLIENT_ID=...
EDGE_SECRET=...
```

### Local development

For local Docker development, copy `pi/.env.example` to `pi/.env` and fill values manually if needed.

| Variable | Description |
|----------|-------------|
| `CLOUD_BASE_URL` | Cloud API base URL, no trailing slash. Local default is `http://host.docker.internal:8000`; production default is `https://api.vendiqo.ch`. |
| `EDGE_CLIENT_ID` | Legacy/manual edge client id, or value written by pairing into `/data/edge.env`. |
| `EDGE_SECRET` | Legacy/manual edge secret, or value written by pairing into `/data/edge.env`. |
| `EDGE_CONFIG_FILE` | Credential file path. Production default: `/data/edge.env`. |
| `DEFAULT_CLOUD_BASE_URL` | Cloud API used during pairing when URL override is disabled. |
| `ALLOW_CLOUD_URL_OVERRIDE` | `true` only in dev; allows the setup UI to choose the cloud URL. |
| `PI_SETUP_UNPAIR_SECRET` | Enables `POST /v1/setup/unpair` with matching `unpair_secret` (factory reset). |
| `DATABASE_URL` | Default: `sqlite:////data/pi.db`. |
| `SYNC_ENABLED` | `1` by default. Set `0` to disable background sync. |
| `SYNC_INTERVAL_SECONDS` | Sync interval in seconds. Default `60`, minimum `15`. |
| `ESCPOS_PRINTER_HOST_OVERRIDE` | Optional. Redirect all TCP print jobs to one reachable host (e.g. a LAN printer IP). Omit to use printer IPs from the synced cloud bundle. |

## Production Docker stack

Production compose:

```text
pi/docker-compose.prod.yml
```

Services:

- `pi-backend`: FastAPI + SQLite + sync/print workers
- `pi-frontend`: nginx static PWA, reverse-proxies `/v1/*` to backend

The production frontend is exposed on port 80, so devices use:

```text
http://192.168.192.10
```

The production images are built by:

```text
.github/workflows/pi-docker.yml
```

Published tags (GHCR, public):

```text
ghcr.io/osswald/order-platform:pi-backend-latest
ghcr.io/osswald/order-platform:pi-frontend-latest
ghcr.io/osswald/order-platform:pi-backend-<sha>
ghcr.io/osswald/order-platform:pi-frontend-<sha>
```

On an already-flashed Pi that still points at the wrong registry, copy the updated compose file and run:

```bash
sudo bash pi/deploy/apply-ghcr-images.sh
```

(from a git checkout on the Pi, or copy `pi/deploy/pi.prod.env` and `pi/docker-compose.prod.yml` to `/opt/vendiqo/pi/` then `sudo docker compose -f /opt/vendiqo/pi/docker-compose.prod.yml pull && sudo systemctl restart vendiqo-pi`).

## Host deploy assets

Files under `pi/deploy/` are installed into the Raspberry Pi OS image:

| File | Purpose |
|------|---------|
| `install-vendiqo-pi.sh` | Copies compose/systemd/network files into a running Pi or image. |
| `pi.prod.env` | GHCR image tags for `/opt/vendiqo/pi/.env` (optional; defaults are in `docker-compose.prod.yml`). |
| `apply-ghcr-images.sh` | Updates `/opt/vendiqo/pi` on a running Pi and restarts the stack. |
| `networkmanager-vendiqo-eth0.nmconnection` | Static Ethernet config for `192.168.192.10/24` (any wired port). |
| `vendiqo-pi.service` | Starts the production Docker Compose stack on boot. |
| `vendiqo-pi-update.service` | Pulls and restarts updated containers. |
| `vendiqo-pi-update.timer` | Runs container update periodically. |

## SD card image build

Generic headless Pi SD images are built with [sdm](https://github.com/gitbls/sdm) from **[`sd-card-creator/`](../sd-card-creator/README.md)** (`./build-on-ubuntu.sh` in a UTM Ubuntu VM or native Linux). Deploy assets used during customization live under `pi/deploy/` and `pi/docker-compose.prod.yml`.

## Cloud API used by Pi

The Pi authenticates with:

```text
X-Edge-Client-Id
X-Edge-Secret
```

Cloud endpoints:

- `POST {CLOUD_BASE_URL}/edge/v1/pair` - first-boot pairing, creates one SD-card installation credential.
- `GET {CLOUD_BASE_URL}/edge/v1/bundle` - active events, configuration, articles, printer mappings, admin PIN hashes.
- `POST {CLOUD_BASE_URL}/edge/v1/orders` - idempotent order upload by `client_order_id`.

Cloud edge auth also requires an active appliance lending for today UTC. If sync returns:

- **401**: credentials are missing, wrong, or revoked.
- **403**: credentials are valid, but no active appliance lending exists for today.

## Local Pi HTTP API

Setup/sync:

- `GET /v1/setup/status` - pairing/setup status (`allow_cloud_url_override`, `can_unpair`).
- `POST /v1/setup/pair` - pairing code; writes `/data/edge.env` (403 if already paired).
- `POST /v1/setup/unpair` - clear `/data/edge.env` when `PI_SETUP_UNPAIR_SECRET` matches.
- `POST /v1/sync/pull` - download bundle from cloud into SQLite.
- `POST /v1/sync/push` - flush pending outbox to cloud.
- `GET /v1/sync/status` - auto-sync state.
- `GET /v1/bundle` - cached bundle JSON.
- `GET /v1/meta` - last bundle pull time.

Orders/tables:

- `POST /v1/orders` - create local order and enqueue outbox + print jobs.
- `POST /v1/orders/{id}/pay` - legacy order payment endpoint.
- `GET /v1/tables/{table_number}?event_id=` - open table orders and merged line groups.
- `GET /v1/tables/open?event_id=` - all open tables.
- `POST /v1/tables/{table_number}/settle-partial` - split-pay selected quantities.
- `POST /v1/tables/{table_number}/settle` - pay all open orders on a table.

Admin/printing/registers:

- `GET /v1/admin/status` - bundle/admin PIN status.
- `POST /v1/admin/verify` - verify 6-digit Pi admin code.
- `GET /v1/print-jobs` - print queue.
- `POST /v1/printers/test-station-prints` - admin test: one station ESC/POS slip per configured station (Pi Admin → **Testdruck**).
- `POST /v1/printers/test-receipt` - sample payment receipt payload (Android Bluetooth setup).
- register, kitchen, pickup, collective bill, voucher, and receipt endpoints are served from the same backend and consumed only by the Pi PWA.

## Automatic cloud sync

When cloud credentials are configured, the Pi backend runs a background loop, default every 60 seconds:

1. push pending local orders to cloud
2. pull the latest event bundle
3. reapply pending local stock deductions so unsynced local orders are not overwritten by cloud stock

If cloud is unreachable, the Pi keeps serving from SQLite and retries on the next cycle.

Table state (`table_number`, `payment_status`) lives only on the Pi. Cloud receives the order payload including `table_number` when orders are pushed.

## Station printing

Each order is split by station. The cloud bundle contains `printer_hosts` mapping station/register UUIDs to ESC/POS printer hosts.

Receipts are rendered with [python-escpos](https://github.com/python-escpos/python-escpos) into byte payloads (`escpos_payload`); the Pi backend sends those bytes over TCP (or returns them for Android Bluetooth). Optional event logos: `configuration.printing.logo_base64` in the synced bundle (PNG/JPEG). Logos are flattened onto a white background (including transparent PNGs), converted to black-on-white for thermal print, scaled to fit the paper width, and centered.

Station, customer pickup, and voucher slips share one ESC/POS layout: event title and localized time (header row), context row (`Station:` + `Best #` / `Bon #`, or `GUTSCHEIN` + copy index), a **large centered hero** (table number, pickup code, or voucher value), line items with right-aligned prices (customer profile may hide prices via `show_price`), quantity/total row, and a centered footer (`station_receipt` / `customer_receipt` `bottom_line`, voucher default «Einloesung bei Zahlung.», or thank-you + waiter name).

Font sizes for station slips come from cloud **`configuration.printing.station_receipt`** (`size_table_or_pickup`, `size_order_lines`; defaults **xlarge** / **large**). On the Pi, table/pickup codes and voucher values use Epson `GS !` magnification (`ESCPOS_HERO_SCALE`, default **8**, range 1–8).

Optional in `pi/.env`:

- `ESCPOS_LINE_WIDTH` — characters per line (default `48`, 80mm Font A)
- `ESCPOS_TIMEZONE` — IANA zone for `ordered_at` display (default `Europe/Zurich`)
- `ESCPOS_HERO_SCALE` — table/pickup/voucher hero magnification (default `8`)
- `ESCPOS_LOGO_MAX_WIDTH` — logo raster width in dots (default `384`, 80mm)

Local and production printing use **real printer hosts** from the synced cloud bundle (`printer_hosts`). Cloud appliance entries must use IPv4 addresses reachable from the `pi-backend` container. Optionally set `ESCPOS_PRINTER_HOST_OVERRIDE` in `pi/.env` to send all jobs to one host (useful for a single test printer on your LAN), then recreate `pi-backend`.

**Special characters** (German `äöüß`, French `éèîç`, etc.) are encoded as **PC858** with `ESC t 19` by default. If glyphs are wrong on a specific printer, set in `pi/.env`:

- `ESCPOS_ENCODING` — Python codec (default `cp858`)
- `ESCPOS_CODEPAGE` — `ESC t` value matching that encoding (default `19`)

Then recreate `pi-backend`. Admin **Testdruck** prints a centered accent demo line and several font sizes.

The emulator image is AGPL-3.0; use only for local development, not production appliances.

## Kellner PWA

The Vue PWA under `pi/frontend/` talks only to the Pi backend. There is no browser-side offline order queue; offline behavior is handled by the Pi server and SQLite.

Roles:

| Role | Access | Features |
|------|--------|----------|
| Kellner | Event wählen -> Kellner/PIN -> Hub | New orders, table settlement, open tables, stock. |
| Admin | Events -> Admin | Pi API URL, manual sync, auto-sync status, **Testdruck** (probe slip per station). |

The **Pi Admin-Code** is configured in cloud under user/organisation assignment. Hashed admin PINs sync in the bundle as `admin_pin_hashes`; the Pi verifies them locally.

## Ordering behavior

### Stock

Cloud manages event stock under Veranstaltung -> Lagerartikel. The Pi uses event stock from the synced bundle.

| Location | Behavior |
|----------|----------|
| Cloud Lagerartikel | `monitor_stock` / `in_stock` per event. |
| Pi Neue Bestellung | Sold out at 0; quantity capped by stock. |
| Pi `POST /v1/orders` | Local bundle stock is reduced immediately. |
| Pi Lagerbestand | Shows local current stock after orders and sync. |
| Cloud push | Deducts event stock once per `client_order_id`. |

### Additions

Cloud articles can be marked as additions (`is_addition`) and linked to base articles. The Pi addition picker enforces the configured additions and applies price adjustments locally.

### Payment mode

| Cloud mode | Pi behavior |
|------------|-------------|
| `pay_later` | Order remains open; settle later at the table. |
| `pay_now` | Order remains open; Pi opens split-pay after order. |
| `instant` | Order is immediately paid. |

`POST /v1/orders` payload:

- `client_order_id`
- `event_id`
- `table_number`
- optional `waiter_id`
- `lines[]`
- `payments[]`

## Local development

Run cloud and Pi side by side:

| App | Command | URL |
|-----|---------|-----|
| Cloud frontend | `cd cloud/frontend && npm run dev` | `http://localhost:5173` |
| Pi frontend | `cd pi/frontend && npm run dev` | `http://localhost:5174` |

Local Docker:

```bash
cd cloud
docker compose up -d

cd ../pi
cp .env.example .env
docker compose up -d --build
```

For local development, `pi/docker-compose.yml` defaults `CLOUD_BASE_URL` to `http://host.docker.internal:8000` and publishes:

- backend API: `http://localhost:8001`
- Vite Pi PWA: `http://localhost:5174`

Set `VITE_API_BASE` for the Pi PWA if your backend is elsewhere.
