## Why

The Vendiqo Waiter Android app is ready for Google Play distribution, but it currently defaults to a LAN-only Pi URL (`http://192.168.192.10`) and has no automated release pipeline. Google Play review requires reviewers to reach a working backend without venue hardware, while real venues still need the same Play Store APK to connect to their local Pi. Option B solves both: one production APK with LAN default plus first-run connection setup when the Pi is unreachable, backed by a persistent cloud-hosted review instance that stays current with each release.

## What Changes

- Add a **persistent Play review Pi** at `https://play-review.demo.vendiqo.ch` (always-on, not the 24h ephemeral hosted Cloud-Pi sandboxes).
- **Auto-refresh** the review instance whenever new Pi Docker images are published on `main`, and **reset the demo event** (wipe local operational state, re-sync config from cloud) so reviewers always get a clean test environment matching the new code.
- Add **first-run connection setup** in the Pi PWA when the default API base is unreachable (configure and test Pi URL, persist in `localStorage`).
- On the setup screen, offer a **“Use Play review demo”** shortcut that points reviewers at the persistent demo host (venues ignore it).
- Add **GitHub Actions** workflow to build a signed release AAB and upload to Google Play (internal testing first, promote manually).
- Fix Android release **version naming** (remove erroneous `versionNameSuffix`) so Play Console accepts monotonic version codes.
- In **Pi Admin**, show both the **bundled app (frontend) version** and the **Pi backend version** currently running on the device (helps verify deploys and debug version mismatches during Play review).
- Document **manual Play Console steps** (App access credentials, demo waiters, service account) in repo docs.

## Capabilities

### New Capabilities

- `android-play-store-release`: Gradle release builds, GitHub CI, Play Console upload, signing, and versioning for the Waiter Android app.
- `play-review-backend`: Persistent VPS-hosted Pi stack, Caddy routing, demo cloud data, deploy-on-image-publish automation, and full demo reset on each deploy.
- `pi-connection-setup`: Pi frontend first-run flow when the venue Pi is unreachable—URL entry, connectivity test, persistence, and Play review demo shortcut.
- `pi-admin-version-display`: Pi Admin shows bundled frontend version and live Pi backend version from the API.

### Modified Capabilities

<!-- No existing openspec specs cover Android, Play Store, or Pi connection setup. -->

## Impact

- **Android**: `android/app/build.gradle.kts`, new GitHub workflow, signing docs, possible `build.gradle.kts` version fix.
- **Pi frontend**: new connection-setup view/guard, router changes, `api/base.ts` connectivity probe, Admin sync URL surfacing, Admin hub version display (frontend + backend).
- **Pi backend**: version endpoint or extended health/setup response; Docker build injects backend version from repo `VERSION`.
- **Cloud / VPS**: new persistent compose stack (or hosted-pi-manager extension), Caddy snippet for `play-review.demo.vendiqo.ch`, deploy workflow with SSH/API secret.
- **Cloud admin (manual)**: dedicated “Play Review Demo” org, event, waiters with known PINs for App access form.
- **CI**: new workflows chained after `pi-docker.yml`; GitHub secrets for keystore and Play service account.
- **Docs**: `android/README.md`, new `docs/play-store.md` for operator checklist.
