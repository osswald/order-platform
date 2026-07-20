## Context

The **Vendiqo Waiter** Android app (`android/`) wraps the Pi PWA (`pi/frontend/`) in a WebView. Production venues run a Raspberry Pi on the LAN at `http://192.168.192.10` (nginx → pi-backend). The bundled Android frontend is built with `pi/frontend/.env.android` (`VITE_API_BASE=http://192.168.192.10`).

Google Play review happens off-LAN. The repo already has **ephemeral hosted Cloud-Pi** sandboxes (`*.demo.vendiqo.ch`, 24h TTL, max 5, config-event only) and **Pi Docker CI** (`.github/workflows/pi-docker.yml` publishes `ghcr.io/...:pi-*-amd64-latest` on every relevant `main` push). There is no Android CI, no Play Console integration, and no persistent demo backend.

**Distribution choice (Option B):** One Play Store APK for all waiters. Default API base remains the venue LAN convention. When the Pi is unreachable, the app shows connection setup. Play reviewers use the same APK and connect to a persistent public demo host via setup (with a one-tap shortcut).

## Goals / Non-Goals

**Goals:**

- Pass Google Play review with a working demo backend reachable from anywhere.
- Keep a **single production APK** on Play Store; venues configure their Pi URL on first run when needed.
- Auto-refresh the review backend when Pi images update on `main`, resetting demo operational data so each deploy starts from a clean test event.
- Automate signed AAB builds and upload to Play Console (internal testing track first).
- Document operator steps outside the codebase (Play Console, demo data, secrets).
- Show frontend and backend version in Pi Admin so operators can confirm the running Pi matches the bundled app after deploys.

**Non-Goals:**

- Replacing sideload/MDM distribution for venues that prefer it.
- Making Stripe Tap to Pay or Bluetooth printing work in review without hardware.
- Baking a review-only API URL as the only default (Option A/C variants).
- Extending ephemeral event sandboxes for review (24h TTL is unsuitable).
- Auto-promoting Play releases to production without human approval (initially).

## Decisions

### 1. Persistent review stack (not ephemeral hosted Pi)

**Decision:** Deploy a dedicated always-on Docker Compose stack on the production VPS at `play-review.demo.vendiqo.ch`, separate from per-event hosted Cloud-Pi.

**Rationale:** Hosted Pi instances expire after 24h, require a config-status event, and use random subdomains. Play review can span days.

**Structure:** Mirror `cloud/hosted-pi-manager/app/compose.py` layout:

- `pi-backend` with `HOSTED_PI=1`, pre-injected edge credentials, `PRINTER_MODE=emulated`, `SYNC_ENABLED=1`
- `pi-frontend` nginx image
- Caddy snippet (reuse hosted-pi-manager Caddy pattern) for TLS + reverse proxy
- Fixed subdomain `play-review` (12-char hex slug not needed; use dedicated compose project name `play-review-pi`)

**Alternative considered:** Extend `hosted_pi_service.py` with infinite TTL and fixed slug. Rejected: couples review lifecycle to event admin UI and hosted-pi quotas.

### 2. Review instance refresh trigger

**Decision:** New workflow `.github/workflows/play-review-deploy.yml` runs after successful `pi-docker.yml` on `main` (using `workflow_run`).

**Steps:** SSH to VPS → `docker compose pull` → **reset demo state** → `docker compose up -d` → `POST /v1/sync/pull` → smoke `GET https://play-review.demo.vendiqo.ch/v1/health` (or setup status).

**Alternative considered:** Deploy only on semver release tags. Rejected: review instance would lag during multi-day reviews between releases.

### 2b. Demo event reset on every code deploy

**Decision:** Each play-review deploy SHALL reset the review Pi to a clean demo state before serving traffic. “Code update” means a successful `pi-docker.yml` run on `main` that triggers `play-review-deploy`.

**Reset scope:**

- **Wipe:** Pi SQLite operational data (orders, shifts, open tables, outbox, local session state in DB) by recreating the `pi-data` Docker volume (e.g. `docker compose down`, remove volume, `up -d`).
- **Preserve:** Edge credentials (`edge.env` / env-injected pairing) so the Pi stays pre-paired; cloud-side demo event config (products, waiters, layout) unchanged in cloud admin.
- **Refresh:** After restart, run `POST /v1/sync/pull` to load the latest bundle from cloud into the fresh DB.

**Rationale:** Reviewers and internal testers should not inherit stale orders or broken state from a previous version. A clean slate also makes smoke tests deterministic after each deploy.

**Alternative considered:** Sync pull only, no volume wipe. Rejected: operational rows from older app versions could leave the demo in an inconsistent state.

**Alternative considered:** Reset cloud event data via admin API on each deploy. Rejected: unnecessary mutation of cloud; local Pi reset + sync pull is sufficient.

### 3. Option B connection setup (Pi frontend)

**Decision:** On app startup (Android and browser), probe connectivity to the current API base (`GET /v1/setup/status` or `/v1/health`). If network error, route to a new **`/connection-setup`** view before setup/pairing guards.

**Setup view provides:**

- Text field for Pi API base URL (normalized, no trailing slash)
- **Test connection** button (probe endpoint, show success/error)
- **Save and continue** → persist via existing `setApiBase()` / `localStorage` key `pi_api_base`
- **Use Play review demo** button → sets `https://play-review.demo.vendiqo.ch`, tests, saves (visible label; venues ignore)

**Default unchanged:** `http://192.168.192.10` for Android builds (`.env.android`). Venues on the standard IP need no setup.

**Alternative considered:** Build flavor with baked demo URL for review only. Rejected under Option B (one Play Store APK).

### 4. Android release versioning

**Decision:** Remove `versionNameSuffix = "0.1"` from release build type. `versionCode` derived from root `VERSION` file (already implemented) must monotonically increase for Play Console.

### 5. GitHub → Play Console CI

**Decision:** New workflow `.github/workflows/android-release.yml`:

- **Trigger:** `workflow_dispatch` (track input: internal/beta/production) initially; optionally `push` tags `v*.*.*` later.
- **Runner:** `ubuntu-latest`, JDK 17, Node 24 (match AGENTS.md).
- **Build:** `./gradlew bundleRelease` (no `VITE_API_BASE` override — LAN default + setup flow handles review).
- **Sign:** Decode `ANDROID_KEYSTORE_BASE64` secret → `android/keystore.properties`.
- **Upload:** `r0adkll/upload-google-play-action` with `PLAY_STORE_SERVICE_ACCOUNT_JSON`, `packageName: ch.vendiqo.app`, `releaseFiles: app-release.aab`.

**Alternative considered:** Fastlane. Deferred; upload action is sufficient for AAB-only flow.

### 6. Demo cloud data (manual seed)

**Decision:** Operators create a **Play Review Demo** organisation in cloud admin with a permanent event, products, and waiters (known PINs). The review Pi edge credential is provisioned once and stored in VPS env/secrets. Each deploy wipes local Pi state and sync-pull refreshes the bundle from cloud (see §2b).

Document waiter names/PINs in `docs/play-store.md` for Play Console App access form.

### 7. Play Console App access copy

**Decision:** Document English instructions (not in code):

1. Install app from internal testing link.
2. On connection setup, tap **Use Play review demo** (or enter URL manually).
3. Log in as waiter `{name}` / PIN `{pin}`.
4. Bluetooth printer and Tap to Pay require hardware; use cash payment to test ordering.

### 8. Pi Admin version display (frontend + backend)

**Decision:** Pi Admin hub (and optionally setup pairing footer) SHALL show two version lines:

- **App (frontend):** existing `useAppVersion()` label (`v{VERSION} ({buildTime})`) — version baked into the bundled/served Pi PWA at build time.
- **Pi backend:** fetched at runtime from the Pi API (extend `GET /v1/health` or add `GET /v1/version`) using the same semver + build-time convention as the frontend (`VERSION` + commit/build time injected at Docker image build).

**Rationale:** After play-review deploys or venue updates, operators can see at a glance whether the WebView/app bundle and the Pi backend are on the expected release. Especially useful when Android bundles an older frontend than the Pi nginx serves, or vice versa.

**UI:** Replace single `Vendiqo Pi {{ label }}` footer with e.g. `App {{ frontendLabel }}` and `Pi {{ backendLabel }}` on `AdminHubView.vue`. If backend is unreachable, show `Pi —` or omit backend line.

**Alternative considered:** Only show backend version. Rejected: frontend version already exists and both are needed to spot mismatch.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Review instance down during Play review | Health-check in deploy workflow; alert on failure; persistent stack with `restart: unless-stopped` |
| Venue waiter opens app off-LAN before event | Connection setup explains venue Wi‑Fi requirement; optional retry on LAN |
| `versionCode` collision if VERSION not bumped | Release workflow only uploads on tagged releases; document that Play uploads require `release:*` merge |
| GHCR pull auth on VPS | VPS `docker login ghcr.io` with read token (document in deploy docs) |
| Cleartext HTTP to venue Pi | Existing `usesCleartextTraffic`; declare in Data safety; HTTPS only for review demo |
| Stripe Terminal permissions flagged in review | App access note + cash-only demo event |
| Setup screen adds friction for standard 192.168.192.10 venues | Probe is fast; only show setup on failure |
| Deploy reset disrupts an in-progress Play review | Reset only on `main` image publish; avoid redeploy during active review windows when possible; review state is ephemeral by design |
| Volume wipe fails mid-deploy | Deploy script stops on error; health check fails; stack not marked healthy until sync pull succeeds |

## Migration Plan

1. **Infra:** Provision persistent compose + Caddy on VPS; seed edge credentials and cloud demo data (manual).
2. **Code:** Connection setup UI + deploy workflow + Android version fix (feature branch → PR).
3. **Secrets:** Add GitHub secrets (keystore, Play service account, VPS SSH key).
4. **Play Console:** Create app, complete App content, manual first AAB upload to internal testing.
5. **CI:** Enable `android-release.yml` workflow_dispatch; verify internal track install.
6. **Review:** Submit with App access instructions; promote through tracks after approval.
7. **Rollback:** Revert compose on VPS; previous AAB remains on Play; connection setup falls back to manual URL entry.

## Open Questions

- Exact demo waiter names/PINs and event configuration (operator decision in cloud admin).
- Closed testing vs internal testing as default CI upload track (recommend **internal** until first approval).
