# Google Play — Vendiqo Waiter (Android)

Operator checklist for publishing **Vendiqo Waiter** (`ch.vendiqo.app`) and maintaining the Play review backend.

## Architecture (Option B)

- **One Play Store APK** for all venues; default Pi URL `http://192.168.192.10`.
- If the Pi is unreachable, the app shows **Pi-Verbindung** setup (URL test + save).
- **Demo** shortcut → `https://play-review.demo.vendiqo.ch`.
- Review backend resets (full `pi-data` wipe) on every Pi image deploy to `main`.
- Nightly cleanup clears demo orders/emulated receipts using the same purge as event **test → prod** (no status change, no volume wipe).

---

## 1. Google Play Console (manual)

### 1.1 Developer account and app

- [ ] Register at [Google Play Console](https://play.google.com/console) ($25 one-time).
- [ ] Create app **Vendiqo Waiter**, package `ch.vendiqo.app`.
- [ ] Category: Business (or Food & Drink).
- [ ] Store listing states the app requires a **Vendiqo Pi / venue server** on the local network.

### 1.2 App content

- [ ] **Privacy policy:** `https://www.vendiqo.ch/datenschutz/`
- [ ] **Data safety:** location, Bluetooth, device identifiers (Stripe Terminal); local network / cleartext HTTP to venue Pi.
- [ ] **Ads:** No.
- [ ] **Content rating** (IARC questionnaire).
- [ ] **Target audience:** not for children.

### 1.3 Play App Signing

- [ ] Enable **Google Play App Signing**.
- [ ] Generate upload keystore (keep offline backup):

  ```sh
  keytool -genkey -v -keystore order-platform-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
  ```

- [ ] Register upload certificate in Play Console.

### 1.4 Play Developer API

- [ ] Google Cloud project → enable **Google Play Android Developer API**.
- [ ] Create service account; download JSON key.
- [ ] Play Console → Users and permissions → invite service account with **Release to testing tracks** (and production when ready).

### 1.5 GitHub secrets

| Secret | Purpose |
|--------|---------|
| `ANDROID_KEYSTORE_BASE64` | Base64 of upload `.jks` |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password |
| `ANDROID_KEY_ALIAS` | Key alias (e.g. `upload`) |
| `ANDROID_KEY_PASSWORD` | Key password |
| `PLAY_STORE_SERVICE_ACCOUNT_JSON` | Full service account JSON |
| `PLAY_REVIEW_DEPLOY_HOST` | VPS hostname |
| `PLAY_REVIEW_DEPLOY_USER` | SSH user |
| `PLAY_REVIEW_DEPLOY_SSH_KEY` | Private key for deploy |
| `PLAY_REVIEW_DEPLOY_PATH` | Repo path on VPS (e.g. `/opt/vendiqo/order-platform`) |
| `PLAY_REVIEW_CLEANUP_SECRET` | Shared secret for nightly Pi `/v1/ops/purge-operational` (also in VPS `cloud/play-review/.env`) |

Encode keystore: `base64 -i order-platform-upload.jks | pbcopy`

### 1.6 Play Review Demo (cloud admin)

- [ ] Create organisation **Play Review Demo** in `admin.vendiqo.ch`.
- [ ] Create a permanent event with products, layout, **cash** payment type.
- [ ] Create demo waiters; record names and PINs below:

  | Waiter | PIN |
  |--------|-----|
  | Martina Meier | `0000` |
  | Martin Müller | `0000` |

  (Event: **Play Review Demo**, currently live on `https://play-review.demo.vendiqo.ch`)

- [x] Create server appliance + pairing; provision edge credentials for the review Pi.
  - Appliance: **Atalanta** (id 69), edge client `ef95471644a24db9aacf4f5041b39c9f`
  - Credentials stored in `/root/order-platform/cloud/play-review/.env` on VPS `178.105.186.26`

### 1.7 VPS review stack

- [x] Copy `cloud/play-review/.env.example` → `.env` on VPS; set `EDGE_CLIENT_ID`, `EDGE_SECRET`, `PLAY_REVIEW_CLEANUP_SECRET`.
- [x] Install Caddy snippet into `cloud/hosted-snippets/play-review.caddy` (project `play-review`).
- [x] Run deploy / `docker compose … up -d` — verified `https://play-review.demo.vendiqo.ch/health` returns JSON `{"status":"ok",...}` with CORS for Android WebView.

Redeploy / full reset demo:

```sh
ssh root@178.105.186.26 'cd /root/order-platform && ./scripts/deploy-play-review.sh'
```

Nightly operational cleanup (test→prod-style purge; keeps pairing):

```sh
ssh root@178.105.186.26 'cd /root/order-platform && ./scripts/cleanup-play-review.sh'
```

Or rely on `.github/workflows/play-review-cleanup.yml` (daily ~03:00 UTC).

### 1.8 App access (Play Console → App content → Sign-in details)

Use **All or some functionality is restricted**. English instructions:

```
1. Install the app from the internal testing link.
2. On first launch, when asked for Pi connection, tap "Demo"
   (this connects to https://play-review.demo.vendiqo.ch and continues automatically;
   or enter that URL manually, tap "Verbindung testen", then "Speichern und fortfahren").
3. Log in as waiter: Martina Meier / PIN: 0000

   (also: Martin Müller / 0000)
4. Open an event, place a test order, pay with cash.
5. Bluetooth printer and Tap to Pay require hardware; not required for review.
```

---

## 2. CI workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| `pi-docker.yml` | Push to `main` | Build Pi images |
| `play-review-deploy.yml` | After Pi Docker on `main` | SSH deploy + demo reset |
| `play-review-cleanup.yml` | Daily schedule (~03:00 UTC) | SSH test→prod-style operational purge |
| `android-release.yml` | Manual dispatch | Build AAB → Play track |

### First Android upload

1. Complete secrets in §1.5.
2. Actions → **Android release** → Run workflow → track **internal**.
3. Play Console → internal testing → install on device.
4. Verify connection setup → demo → waiter login.

### Version codes

`versionCode` is derived from repo [`VERSION`](../VERSION) (`major*10000 + minor*100 + patch`). Each Play upload requires a merged PR with a `release:patch|minor|major` label so `VERSION` increases.

---

## 3. Troubleshooting

| Issue | Check |
|-------|--------|
| Review host down | `curl -fsS https://play-review.demo.vendiqo.ch/health` must return JSON (`"status":"ok"`), not HTML |
| Demo button fails in Android | Confirm CORS: `curl -sSI -H 'Origin: https://appassets.androidplatform.net' https://play-review.demo.vendiqo.ch/health` includes `Access-Control-Allow-Origin` |
| Stale demo orders / receipts | `./scripts/cleanup-play-review.sh` (or wait for nightly); full wipe: `./scripts/deploy-play-review.sh` |
| App stuck on connection setup | Venue Wi‑Fi; correct Pi IP in Admin → Synchronisation |
| Play upload fails signing | GitHub secrets; keystore matches Play upload certificate |

---

## 4. Related docs

- [android/README.md](../android/README.md) — local Android builds
- [cloud/play-review/README.md](../cloud/play-review/README.md) — review VPS stack
- [docs/RELEASE.md](RELEASE.md) — semver and Pi image tags
