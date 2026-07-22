## Context

Android Play Store builds embed the Pi frontend in a WebView served from `https://appassets.androidplatform.net`. Connectivity setup probes `GET {apiBase}/health` via `fetch`. On a venue LAN that hits the Pi; for Play review, the shortcut points at `https://play-review.demo.vendiqo.ch`.

Today that host returns SPA `index.html` for `/health` (nginx `try_files` fallback — typically an older frontend image without the `/health` → backend proxy). Static HTML has no CORS headers, so the WebView blocks the response and the UI shows a network error. A browser visiting the same origin works because navigation is not a cross-origin XHR.

Startup also waits for the OS-level TCP timeout when probing the default `http://192.168.192.10`, so connection setup appears late when offline.

## Goals / Non-Goals

**Goals:**

- Make Play review `/health` a real backend health response with CORS so the existing Android probe + **Demo** shortcut succeed.
- Fail deploy smoke checks if `/health` is HTML or lacks a usable CORS response for the Android WebView origin.
- Bound probe wait time so connection setup appears quickly when no Pi answers.
- Shorten the demo button label to **Demo**.
- Periodically reset Play review operational demo data using the same purge semantics as event **test → prod** (orders and related operational rows; include emulated receipts on the Pi).

**Non-Goals:**

- Changing the probe path away from `/health` (that remains approach B / follow-up if needed).
- Changing Android WebView origin / Capacitor migration.
- Auto-saving the demo URL without the user tapping save (current UX: set URL → test → save).
- Venue LAN discovery (mDNS, QR, etc.).
- Full `pi-data` volume wipe on the schedule (that remains deploy-only).
- Permanently flipping the demo event to `prod` (status stays as operators configured it, typically `test`).

## Decisions

### 1. Fix public `/health` on the review host (approach A), keep probe path

**Decision:** Redeploy / ensure `pi-frontend` nginx proxies `location /health` to `pi-backend:8000/health`. Backend `CORSMiddleware` already allows all origins, so Android `Origin: https://appassets.androidplatform.net` gets ACAO.

**Alternatives considered:**

- Probe `/v1/setup/status` instead (works today with CORS) — good fallback, but leaves `/health` lying to OTA/deploy and does not fix already-shipped APKs that call `/health`. Prefer server fix for immediate unblock + correct health semantics.
- Add CORS headers on nginx for static HTML — would make a false “reachable” probe (HTML 200) and still break Admin hub health JSON parsing.

### 2. Harden deploy health verification

**Decision:** Update `scripts/deploy-play-review.sh` to require `GET $PLAY_REVIEW_URL/health` with:

- HTTP 2xx
- `Content-Type` indicating JSON (e.g. `application/json`)
- Body parseable as health (`status` field present / `"status":"ok"`)
- Optional but recommended: request with `Origin: https://appassets.androidplatform.net` and assert `Access-Control-Allow-Origin` is present (`*` or that origin)

Stop treating bare `curl -fsS …/health` success (SPA HTML) as healthy. Keep `/v1/setup/status` only as a secondary configured check after sync, not as a substitute for `/health` CORS/API correctness.

### 3. Client probe timeout (~2–3s)

**Decision:** `probeApiBase` uses `AbortSignal.timeout(PROBE_TIMEOUT_MS)` (target **2500 ms**) on the health `fetch`. Abort / timeout maps to `reason: 'network'` (same UX as unreachable). Apply on startup and on connection-setup / admin test.

**Rationale:** Unreachable private IPs can hang 30s+ on Android WebView. Venue LAN Pi on the same subnet usually answers in well under 1s; 2.5s is enough margin without feeling stuck.

**Alternatives:** Parallel probe of demo host on startup — out of scope; user still chooses Demo explicitly.

### 4. Button label **Demo**

**Decision:** Replace `Play-Review-Demo verwenden` with **Demo**. Constant URL unchanged (`PLAY_REVIEW_DEMO_API_BASE`). Update docs/Play Console instructions that quote the old label.

### 5. Scheduled cleanup = test→prod purge (not status flip, not volume wipe)

**Decision:** Regular Play review cleanup reuses the same purge behavior as when an event transitions **test → prod**:

| Side | Existing entry point | What it clears |
|------|----------------------|----------------|
| Cloud | `purge_event_operational_data` (called from events CRUD on test→prod) | Edge orders/payments/sessions/snapshots, collective bills, voucher redemptions; stock reset to baseline |
| Pi | `purge_event_local_data` (via `reconcile_bundle_lifecycle` on test→prod in bundle pull) | Orders, kitchen tickets, payments, cash sessions, outbox, counters, etc. for that event |

Do **not** implement cleanup by actually changing status to `prod` (no reverse transition; would freeze OTA and change waiter UX). Instead invoke the purge functions (or a thin shared helper they both call) for the Play Review Demo event id, on a schedule.

**Emulated receipts:** Today Pi `purge_event_local_data` / `purge_all_operational_data` do **not** delete `emulated_receipts`. Extend the Pi purge path used by test→prod (and thus by this schedule) to clear emulated receipts as well, so both paths stay aligned.

**Cadence:** Daily by default (e.g. GitHub `schedule` workflow or VPS cron calling a small script/API). Exact trigger mechanism chosen at apply time; must be documented in `docs/play-store.md`.

**Alternatives considered:**

- Full `docker compose down -v` like deploy — too heavy; drops pairing/DB and needs sync; overkill for stale orders/receipts.
- Status toggle test→prod→… — impossible without breaking the lifecycle graph; rejected.

## Risks / Trade-offs

- **[Risk] Published `pi-frontend-amd64-latest` still lacks `/health` proxy** → Deploy fails hard after smoke-check tightening; rebuild/publish Pi images or pin a known-good digest, then redeploy.
- **[Risk] Short timeout false-negatives on slow cellular to review host** → 2.5s is usually enough for HTTPS to VPS; if needed, raise slightly for demo-only path later (not in this change).
- **[Risk] `AbortSignal.timeout` unsupported on very old WebViews** → Target devices for Play Store are modern; if needed, polyfill via `AbortController` + `setTimeout`.
- **[Trade-off] Already-installed apps still wait long until a new AAB ships** → Ops `/health` fix unblocks Demo immediately; timeout UX needs a frontend release.
- **[Risk] Cleanup mid-review wipes an active reviewer’s open tables** → Acceptable for a shared demo; document cadence; prefer off-peak schedule (e.g. nightly UTC).
- **[Risk] Cloud purge without Pi purge (or vice versa) leaves resurrectable mirror state** → Cleanup job MUST purge cloud and trigger Pi-side purge (direct API or sync path that runs `purge_event_local_data`) in one run.

## Migration Plan

1. Land code: probe timeout + Demo label + deploy script hardening + purge extension (emulated receipts) + scheduled cleanup (PR).
2. Confirm GHCR `pi-frontend-amd64-latest` includes nginx `/health` proxy (from Play Store pipeline commit); if not, ensure `main` has built images.
3. Run `./scripts/deploy-play-review.sh` on the VPS (or let `play-review-deploy.yml` run); verify JSON `/health` + CORS.
4. Retest internal testing APK Demo button without waiting for a new build (server-side fix).
5. Enable/verify scheduled cleanup once; confirm orders + emulated receipts cleared and event still `test`/paired.
6. Ship Android release with timeout + label when convenient.

**Rollback:** Revert deploy script checks if too strict mid-incident; rollback VPS compose to previous images only if new images break sync (unlikely for nginx location add); disable schedule if cleanup misfires.

## Open Questions

- Exact timeout value: default **2500 ms** unless product prefers 2s or 3s at apply time.
- Exact daily time / timezone for cleanup (default: nightly UTC).
