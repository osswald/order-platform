## Why

Google Play internal testers (and reviewers) who are not on a venue LAN reach the Pi connection setup screen, but tapping the Play review demo shortcut fails with "Pi nicht erreichbar" even though `https://play-review.demo.vendiqo.ch` works in a browser. The Android WebView probes `GET /health` cross-origin; the live review host currently serves SPA HTML for `/health` without CORS headers, so `fetch` fails. Separately, waiting for the default LAN Pi (`192.168.192.10`) to time out makes that setup screen appear too slowly, and the demo button label is longer than needed.

## What Changes

- Ensure the Play review host's public `GET /health` is the Pi backend health JSON (via frontend nginx proxy), with CORS usable from the Android WebView origin (`https://appassets.androidplatform.net`), so the existing demo shortcut works without changing the probe path.
- Harden play-review deploy smoke checks so a 200 HTML SPA response cannot pass as healthy.
- Add a short client-side timeout to the Pi connectivity probe so connection setup appears quickly when no Pi is reachable.
- Rename the connection-setup demo button label to **Demo** (still targets `https://play-review.demo.vendiqo.ch`).
- On a regular schedule, clean the Play review demo the same way as an event **test → prod** transition: purge operational orders/related local+cloud data (and emulated receipts on the Pi), without changing the demo event’s lasting status or wiping pairing/`pi-data`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `play-review-backend`: Public `/health` MUST return backend health JSON (not SPA HTML); deploy verification MUST reject non-API health responses; scheduled cleanup MUST reuse test→prod purge semantics (orders + emulated receipts).
- `pi-connection-setup`: Probe MUST fail fast on unreachable Pi; demo shortcut button label is **Demo**.

## Impact

- VPS play-review stack: redeploy with a `pi-frontend` image that proxies `/health`; update `scripts/deploy-play-review.sh` (and related docs/compose healthcheck expectations); add scheduled cleanup wiring.
- Pi backend: ensure emulated receipts are included in the same purge path used for test→prod / play-review cleanup (today `purge_event_local_data` does not delete `emulated_receipts`).
- Cloud backend: reuse `purge_event_operational_data` (or equivalent) for the demo event on the schedule.
- Pi frontend: `probeApiBase` timeout; `ConnectionSetupView` button copy (+ tests / i18n if any).
- Android Play Store build picks up frontend changes on next release; ops `/health` fix can unblock already-installed builds that already probe `/health`.
