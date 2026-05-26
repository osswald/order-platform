# Raspberry Pi edge (venue server)

On-prem stack: **FastAPI** + **SQLite** + **PWA** for waiters. Pulls event bundles from **cloud** using device credentials (`X-Edge-Client-Id` / `X-Edge-Secret`) on the server appliance.

## Hybrid SD / Docker updates

1. Flash a small Raspberry Pi OS image with Docker and a one-shot bootstrap (copy `EDGE_CLIENT_ID` and `EDGE_SECRET` from cloud admin after creating or rotating server appliance credentials).
2. On each boot, run `docker compose pull` (host cron or systemd) so images update from your registry.
3. Container images are built in CI (see `.github/workflows/pi-docker.yml`) and stored in **GHCR** (or any registry). The Pi only **pulls** images; it does not run cloud workloads.

## Headless first-boot pairing

The production Pi image is intended to boot headlessly on the Verleiher router with a fixed Ethernet address:

```text
eth0:    192.168.192.10/23
gateway: 192.168.192.1
dns:     192.168.192.1
```

When the Pi has no edge credentials, open `http://192.168.192.10` from a device on the same router network. In cloud admin, open the server appliance and create a short-lived pairing code. Enter that code on the Pi setup page. The Pi calls `POST /edge/v1/pair`, receives `EDGE_CLIENT_ID` and `EDGE_SECRET` once, and stores them in `/data/edge.env` on the persistent Docker volume.

Image/build assets live in `pi/deploy/`:

- `networkmanager-vendiqo-eth0.nmconnection` sets `192.168.192.10/23`
- `vendiqo-pi.service` starts `docker compose -f docker-compose.prod.yml up -d`
- `vendiqo-pi-update.timer` periodically pulls new container images
- `install-vendiqo-pi.sh` installs these files into a Raspberry Pi OS image or running Pi

## Environment (`pi/.env` or compose `environment`)

| Variable | Description |
|----------|-------------|
| `CLOUD_BASE_URL` | Cloud API base URL (no trailing slash). Docker defaults to `http://host.docker.internal:8000` so the Pi container can reach cloud on the host. Production: `https://api.example.com` |
| `EDGE_CLIENT_ID` | From cloud `ApplianceAdminCreated.edge_client_id` |
| `EDGE_SECRET` | Plain secret shown once at create/rotate |
| `DATABASE_URL` | Default `sqlite:////data/pi.db` (use volume `/data`) |
| `SYNC_ENABLED` | `1` (default): background push/pull when cloud credentials are set; `0` to disable |
| `SYNC_INTERVAL_SECONDS` | Seconds between sync attempts (default `60`, minimum `15`) |

## Cloud API used by Pi

- `GET {CLOUD_BASE_URL}/edge/v1/bundle` — active events + configuration + article snapshot  
- `POST {CLOUD_BASE_URL}/edge/v1/orders` — idempotent order upload (`client_order_id`)

## Local Pi HTTP API (LAN)

- `POST /v1/sync/pull` — download bundle from cloud into SQLite  
- `POST /v1/sync/push` — flush pending outbox to cloud (manual; auto sync also pushes)  
- `GET /v1/sync/status` — auto-sync state (`configured`, `last_cycle_at`, pending outbox count, …)  
- `GET /v1/bundle` — cached bundle JSON  
- `GET /v1/meta` — last bundle pull time  
- `POST /v1/orders` — create local order (`table_number` required) + outbox + **one print job per station** (only that station’s lines)  
- `POST /v1/orders/{id}/pay` — pay one order (legacy API; frontend uses split pay via `settle-partial`)  
- `GET /v1/tables/{table_number}?event_id=` — open orders + `line_groups` (merged qty per article) for split pay  
- `GET /v1/tables/open?event_id=` — list all tables with unpaid orders (summary per table)  
- `POST /v1/tables/{table_number}/settle-partial` — pay selected line qty (split pay)  
- `POST /v1/tables/{table_number}/settle` — pay all open orders on a table  
- `GET /v1/admin/status` — whether bundle exists and admin PIN is required  
- `POST /v1/admin/verify` — verify 6-digit Pi admin code (against hashes from synced bundle)  
- `GET /v1/print-jobs` — list print job queue (ESC/POS worker)  

### Automatic cloud sync

When `CLOUD_BASE_URL`, `EDGE_CLIENT_ID`, and `EDGE_SECRET` are set, the Pi backend runs a background loop (default every **60 s**): **push** pending orders to the cloud, then **pull** the latest bundle. If the cloud is unreachable, the Pi keeps serving waiters from the cached bundle and local SQLite; sync retries on the next interval.

After each pull, stock levels are adjusted again for orders not yet acknowledged by the cloud so local deductions are not overwritten.

The Kellner-PWA refreshes the cached bundle from the Pi API (not directly from the cloud) while the tab is visible.

Table state (`table_number`, `payment_status` open/paid) lives **only on the Pi**; cloud receives the same JSON payload including `table_number` on push.

### Station printing

Each order is split by `station_id` on the lines (missing ids are inferred from the event station config). Every station gets its own voucher to the printer mapped in the bundle (`printer_hosts` per station id).

### Testing: print to file

Set in `pi/.env`:

```env
PRINT_TO_FILE=1
PRINT_OUTPUT_DIR=/data/print-vouchers
```

Restart `pi-backend`. Vouchers are written as `.txt` under that directory (on Docker: volume `pi-data`, path `/data/print-vouchers`). Network printers are not contacted. One file per station per order.

```bash
docker compose exec pi-backend ls -la /data/print-vouchers
```

## Kellner-PWA (Mobil)

Die Vue-PWA unter [pi/frontend/](pi/frontend/) spricht **nur** den Pi-Backend. **Keine** Offline-Warteschlange im Browser.

### Kellner vs. Admin

| Rolle | Zugang | Funktionen |
|-------|--------|------------|
| **Kellner** | Event wählen → Kellner/PIN → Hub | Neue Bestellung, Tisch abrechnen, **Offene Tische**, **Lagerbestand** |
| **Admin** | Startseite **Events** → **Admin** | Pi-API-URL, manueller Sync (pull/push), Auto-Sync-Status |

Der **Pi Admin-Code** (6 Ziffern) wird in der **Cloud** unter Benutzer → Organisationen zuordnen → Feld **Pi Admin-Code** gesetzt. Beim Sync landen gehashte Codes im Bundle (`admin_pin_hashes`); der Pi prüft den Code lokal. Die Admin-Session gilt nur für diesen Browser-Tab (`sessionStorage`).

**Erstinbetriebnahme:** App öffnen → **Events** → **Admin** (ohne Code, solange noch kein Bundle bzw. keine PIN-Hashes) → **Konfiguration laden** → Events erscheinen für Kellner. Nachdem in der Cloud ein Pi Admin-Code gesetzt wurde: erneut syncen; danach verlangt **Admin** den 6-stelligen Code.

**Kellner-Ablauf:** Event → Kellner/PIN → **Hub** → **Neue Bestellung** (Tischnummer 1–99999) → **Split-Screen** (Warenkorb oben, Layout-Grid unten) → **FERTIG**. Optional **Tisch abrechnen** oder **Offene Tische** für offene Posten (`pay_later`). **Lagerbestand** zeigt Artikel mit `monitor_stock` und `in_stock` aus dem Bundle.

### Lagerbestand (pro Event)

In der **Cloud** unter Veranstaltung → **Lagerartikel** (Tab): alle an Stationen verknüpften Artikel, **Bestand führen** und **Bestand** pro Event (`event_article_stock`). Beim Bundle-Sync und bei Bestellungen gilt dieser Event-Bestand (nicht der globale Artikel-Stammdaten-Bestand).

| Ort | Verhalten |
|-----|-----------|
| Cloud **Lagerartikel** | `monitor_stock` / `in_stock` pro Event speichern |
| Pi **Neue Bestellung** | Ausverkauft bei 0; Hinweis „Nur noch N verfügbar“; Menge begrenzt |
| Pi **FERTIG** (`POST /v1/orders`) | Bestand im lokalen Bundle wird reduziert; Response enthält `articles`-Patch |
| Pi **Lagerbestand** | Aktuelle Werte (nach Bestellung + bei Tab-Wechsel Sync) |
| Cloud (Push) | `POST /edge/v1/orders` reduziert Event-Bestand einmal pro `client_order_id` |

Artikel nur im App-Layout (ohne Station) erscheinen nicht unter Lagerartikel; im Bundle sind sie ohne Bestandsführung verkaufbar, solange sie nicht auch einer Station zugeordnet sind.

### Zusätze (Additions)

In der **Cloud** unter **Artikel**: Typ **Zusätze** anlegen (`is_addition`). **Preis** des Zusatzes: `0` = kostenlos, positiv = Aufpreis, negativ = Abzug vom Artikelpreis. Am **Basisartikel** (Artikel bearbeiten → Abschnitt Zusätze) die erlaubten Zusätze verknüpfen.

| Schritt | Verhalten |
|---------|-----------|
| Kellner wählt Artikel mit Zusätzen | Pflicht-Dialog **Zusätze** (0..n wählbar, auch leer bestätigen) |
| Warenkorb / FERTIG | Zeile enthält `additions: [{ article_id, qty }]`; Preis = Basis + Summe Zusatzpreise (min. 0 pro Stück) |
| Lager | Zusätze mit Bestandsführung in **Lagerartikel** und bei Bestellung wie Artikel abgezogen |
| Druck | Bon listet Zusätze unter der Position |

Zusätze erscheinen nicht im Layout-Grid (nur über den Zusatz-Dialog am Basisartikel).

### Split pay (Tisch abrechnen)

**Tisch abrechnen** öffnet den Teilbetrag-Bildschirm (Vollbild): oben Positionen für die aktuelle Zahlung, unten Rest des Tisches (`verbleibend / gesamt`). Unten antippen (+1 in den Teilbetrag), oben: **Menge** = Popup, **Name** = +1, **Preis** = −1. Grüner Haken = Teilbetrag sofort verbuchen (kein Bargeld-Keypad).

### `payment_mode` nach FERTIG

| Modus (Cloud) | Verhalten |
|---------------|-----------|
| `pay_later` | Bestellung **offen**; Abrechnung am Tisch (Split pay) |
| `pay_now` | Bestellung **offen**; nach FERTIG direkt **Split-Pay-Bildschirm** am Tisch |
| `instant` (**Sofort bezahlt**) | Nach FERTIG sofort **bezahlt**, kein Zahlungsbildschirm (Rechnung später / gratis Events) |

### Payload `POST /v1/orders`

- `client_order_id`, `event_id`, **`table_number`** (1–99999), `waiter_id?`, `lines[]`, `payments[]`
- `lines`: `{ article_id, qty, station_id?, note?, additions?: [{ article_id, qty }] }`
- `payments`:
  - **`pay_later` / `pay_now`:** `[]` bei Bestellung; Zahlung via `POST /v1/tables/{n}/settle-partial` (Split pay) oder `settle`
  - **`instant`:** automatisch `[{ "type": "instant", "amount_cents": N }]` beim Anlegen (Summe = Zeilensumme in Cent)

PWA in Docker: compose maps host **5174** → container **5174** (same Vite port as local `npm run dev`). Cloud frontend can stay on **5173** when you run both on one machine.

## Local dev next to cloud

| App | Command | URL |
|-----|---------|-----|
| Cloud frontend | `cd cloud/frontend && npm run dev` | http://localhost:5173 |
| Pi frontend | `cd pi/frontend && npm run dev` | http://localhost:5174 |

Set `VITE_API_BASE` for the Pi PWA to your Pi backend (e.g. `http://127.0.0.1:8001`). Cloud UI continues to use its own `api.js` against the cloud backend.

## Local Docker: Pi + cloud on one machine

1. Start cloud: `cd cloud && docker compose up -d` (API on host **http://localhost:8000**).
2. In cloud admin: create org, an **active event** (start/end including **today UTC**), a **server** appliance with edge credentials, and an **appliance lending** covering today.
3. Copy **edge client id** and **edge secret** from the cloud admin UI into `pi/.env` as `EDGE_CLIENT_ID` and `EDGE_SECRET` (they must be non-empty — blank values produce a **503** with a `missing` list on sync).
4. Start Pi: `cd pi && docker compose up -d --build`.

`pi/docker-compose` sets **`CLOUD_BASE_URL`** to `http://host.docker.internal:8000` by default so `pi-backend` can reach cloud (inside a container, `localhost` would not be the host). **`VITE_API_BASE`** defaults to `http://localhost:8001` so the PWA in your browser talks to the published Pi API.

If sync returns **403** from cloud, check **appliance lending** dates (cloud edge auth requires an active lending for “today” in UTC). If **401**, check edge id/secret. If the Pi container cannot resolve `host.docker.internal`, ensure Docker is recent enough that `extra_hosts: host-gateway` works (Compose file already adds it for Linux).

On venue LAN, point phones to the Pi host and the port you expose (e.g. Caddy/nginx in front of the PWA).
