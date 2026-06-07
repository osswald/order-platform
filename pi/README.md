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

The cloud only returns `EDGE_SECRET` once during pairing. The Pi backend reads credentials from `/data/edge.env`.

**Setup lockdown (production):**

- `POST /v1/setup/pair` is rejected with **403** if the Pi is already paired (`/data/edge.env` exists).
- Pairing always uses `DEFAULT_CLOUD_BASE_URL` (default `https://api.vendiqo.ch`).
- `POST /v1/setup/unpair` revokes the active SD-card credential in cloud first, then clears local credentials when `PI_SETUP_UNPAIR_SECRET` is set on the Pi and the request body includes the matching `unpair_secret`.

Local Docker dev should set `DEFAULT_CLOUD_BASE_URL=http://host.docker.internal:8000` in `pi/.env`.

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

For local Docker development, copy `pi/.env.example` to `pi/.env` and set the cloud URL for pairing if needed.

| Variable | Description |
|----------|-------------|
| `EDGE_CONFIG_FILE` | Credential file path. Production default: `/data/edge.env`. |
| `DEFAULT_CLOUD_BASE_URL` | Cloud API used during pairing. |
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

New `pi-backend` images are built when `pi/backend/**` changes are pushed to `main` (workflow `pi-docker.yml`). The update timer on the Pi pulls `:pi-backend-latest` about every 15 minutes, or restart `vendiqo-pi.service` immediately after a manual pull.

## Host deploy assets

Files under `pi/deploy/` are installed into the Raspberry Pi OS image:

| File | Purpose |
|------|---------|
| `install-vendiqo-pi.sh` | Copies compose/systemd/network files into a running Pi or image. |
| `pi.prod.env` | GHCR image tags for `/opt/vendiqo/pi/.env` (optional; defaults are in `docker-compose.prod.yml`). |
| `apply-ghcr-images.sh` | Updates `/opt/vendiqo/pi` on a running Pi and restarts the stack. |
| `networkmanager-vendiqo-eth0.nmconnection` | Static Ethernet config for `192.168.192.10/24` on `eth0`. |
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
- `POST {CLOUD_BASE_URL}/edge/v1/sync/operational/chunk` - idempotent chunk upload by `chunk_id` (fallback to `/edge/v1/orders` while migrating).

Cloud edge auth also requires an active appliance lending for today UTC. If sync returns:

- **401**: credentials are missing, wrong, or revoked.
- **403**: credentials are valid, but no active appliance lending exists for today.

## Local Pi HTTP API

Setup/sync:

- `GET /v1/setup/status` - pairing/setup status (`can_unpair`).
- `POST /v1/setup/pair` - pairing code; writes `/data/edge.env` (403 if already paired).
- `POST /v1/setup/unpair` - revoke active cloud SD credential and then clear `/data/edge.env` when `PI_SETUP_UNPAIR_SECRET` matches.
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
- `DELETE /v1/print-jobs/{id}` - dismiss a failed waiter station/kitchen print job (`status=error`, `job_kind` in `station_order` / `kitchen_ticket`).
- `POST /v1/printers/test-station-prints` - admin test: one station ESC/POS slip per configured station (Pi Admin → **Testdruck**).
- `POST /v1/printers/test-receipt` - sample payment receipt payload (Android Bluetooth setup).
- `POST /v1/payments/{payment_id}/receipt` - ESC/POS payload for a payment receipt (Android Bluetooth or reprint).
- `POST /v1/payments/{payment_id}/receipt/print` - enqueue payment receipt to a station/register printer (`station_uuid` must exist in synced `printer_hosts`).
- register, kitchen, pickup, collective bill, voucher, and receipt endpoints are served from the same backend and consumed only by the Pi PWA.

## Automatic cloud sync

When cloud credentials are configured, the Pi backend runs a background loop, default every 60 seconds:

1. pull latest bundle (pre-event / periodic)
2. reconcile rental lifecycle and purge stale event/org data
3. push pending operational chunks to cloud with per-chunk ack
4. reapply pending local stock deductions so unsynced local orders are not overwritten by cloud stock

If cloud is unreachable, the Pi keeps serving from SQLite and retries on the next cycle.

Table state (`table_number`, `payment_status`) lives only on the Pi. Cloud receives the order payload including `table_number` when orders are pushed.

## Station printing

Each order is split by station. The cloud bundle contains `printer_hosts` mapping station/register UUIDs to ESC/POS printer hosts.

Receipts are rendered with [python-escpos](https://github.com/python-escpos/python-escpos) into byte payloads (`escpos_payload`); the Pi backend sends those bytes over TCP (or returns them for Android Bluetooth). Optional event logos: `configuration.printing.logo_base64` in the synced bundle (PNG/JPEG). Logos are flattened onto a white background (including transparent PNGs), converted to black-on-white for thermal print, scaled to fit the paper width, and centered.

Station, customer pickup, and voucher slips share one ESC/POS layout: event title and localized time (header row), context row (`Station:` + `Best #` / `Bon #`, or `GUTSCHEIN` + copy index), a **large centered hero** (table number, pickup code, or voucher value), and line items. **Station kitchen slips** never print prices or totals (quantities and names only) and omit the cloud **Fußzeile**; they end with the **Kellner- or Kassenname**. **Customer pickup** slips (`customer_receipt`) print line prices and a total row when **Preise anzeigen** is enabled in cloud (tab *Kunde / Abholbeleg*), and print the cloud **Fußzeile** (`bottom_line`) or the legacy fallback «Bitte an der Ausgabe abholen.» when empty. **Voucher** slips use the voucher footer («Einloesung bei Zahlung.» or custom `bottom_line`).

Font sizes for station slips come from cloud **`configuration.printing.station_receipt`**: `size_order_lines` controls article lines (**normal** / **large**; default **large** = double height and width), `size_table_or_pickup` controls the table/pickup hero (**normal** / **large** / **xlarge** in cloud UI). Table/pickup codes and voucher values use Epson `GS !` magnification (`ESCPOS_HERO_SCALE`, default **8**, range 1–8). The Kellner-/Kassenname footer is printed centered in Font B (smaller than the header rows).

**Payment receipts** (`configuration.printing.payment_receipt`, cloud tab *Belege*) use compact **normal** line size by default, optional logo and event title (with event label override), and a centered **Fußzeile** (empty = «Danke!»).

Optional in `pi/.env`:

- `ESCPOS_LINE_WIDTH` — characters per line for **network** slips and station payment prints when no `paper_width` is sent (default `48`, 80 mm Font A). Bluetooth payment receipts use the device setting instead (`80mm`→48, `58mm`→32, `53mm`→30).
- `ESCPOS_TIMEZONE` — IANA zone for `ordered_at` display (default `Europe/Zurich`)
- `ESCPOS_HERO_SCALE` — table/pickup/voucher hero magnification (default `8`)
- `ESCPOS_LOGO_MAX_WIDTH` — logo raster width in dots (default `384`, 80mm)

**Zeilenvorschub vor Schnitt** is configured per **Drucker** appliance in cloud admin (**Geräte** → Drucker → *Zeilenvorschub vor Schnitt*, 0–10; default 1). The Pi syncs this via `printer_hosts` in the event bundle.

Local and production printing use **real printer hosts** from the synced cloud bundle (`printer_hosts`). Cloud appliance entries must use IPv4 addresses reachable from the `pi-backend` container. Optionally set `ESCPOS_PRINTER_HOST_OVERRIDE` in `pi/.env` to send all jobs to one host (useful for a single test printer on your LAN), then recreate `pi-backend`.

### Payment receipts (Zahlungsbeleg)

After paying (order, table split-pay, collective bill, or cash-register checkout), the Pi PWA asks **Zahlungsbeleg drucken?** only when the event has **Zahlungsbeleg nach Bezahlung anbieten** enabled in cloud Stammdaten (off by default). If yes:

- **Android with a paired Bluetooth printer** — prints on the device (no station list). Paper width is set per device under **Bluetooth Drucker** (80 mm / 58 mm / 53 mm); narrow Bluetooth printers should use **53 mm** so prices align flush right.
- **Cash register (Kasse)** — prints on the current register's configured Kundendrucker when available (no station list).
- **Otherwise** — lists stations and cash registers that have an entry in `printer_hosts`; the Pi queues a `PrintJob` to the chosen printer (always 80 mm / `ESCPOS_LINE_WIDTH` default).

Reprints from **Belege** use the same flow. Manual checks:

| Scenario | Expected |
|----------|----------|
| Browser + station printer in cloud | Pay → Drucken → pick station → slip prints on network printer |
| Cash register + Kundendrucker configured | Checkout → Drucken → prints on current register printer |
| Android + Bluetooth paired | Pay → Drucken → prints on phone printer, no station list |
| Android + no Bluetooth | Pay → Drucken → station list |
| Nein | No print job, normal navigation |

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
| Admin | Events -> Admin | Entkoppeln (mit Confirm + Werksschlüssel), manual sync, auto-sync status, **Testdruck** (probe slip per station). |

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
