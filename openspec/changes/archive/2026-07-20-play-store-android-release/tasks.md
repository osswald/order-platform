## 1. Operator setup (outside code — document in docs/play-store.md)

- [ ] 1.1 Create Google Play Developer account and app listing for Vendiqo Waiter (`ch.vendiqo.app`)
- [ ] 1.2 Complete Play Console App content (privacy policy, data safety, content rating, ads declaration)
- [ ] 1.3 Enable Play App Signing; generate upload keystore; register upload key fingerprint
- [ ] 1.4 Create Google Cloud service account with Play Developer API; invite in Play Console with release-to-testing permission
- [ ] 1.5 Add GitHub secrets: `ANDROID_KEYSTORE_BASE64`, keystore passwords, `PLAY_STORE_SERVICE_ACCOUNT_JSON`, `PLAY_REVIEW_DEPLOY_SSH_KEY`
- [ ] 1.6 In cloud admin, create **Play Review Demo** org/event with products and demo waiters (document names/PINs for App access)
- [x] 1.7 Provision edge credentials for review Pi; store on VPS as env/secrets for persistent stack
- [ ] 1.8 Fill Play Console **App access** with English reviewer instructions (connection setup → demo shortcut → waiter login)

## 2. Play review backend (VPS)

- [x] 2.1 Add persistent compose stack under `cloud/play-review/` (pi-backend + pi-frontend, `HOSTED_PI=1`, emulated printers)
- [x] 2.2 Add Caddy routing for `play-review.demo.vendiqo.ch` (reuse hosted-pi-manager snippet pattern or document manual VPS Caddy block)
- [x] 2.3 Write deploy script (`scripts/deploy-play-review.sh` or equivalent) — pull images, wipe `pi-data` volume (reset demo event), up -d, `POST /v1/sync/pull`, health check
- [x] 2.4 Add `.github/workflows/play-review-deploy.yml` triggered by successful `pi-docker.yml` on `main`
- [x] 2.5 Verify manual deploy: setup status configured, demo waiter login works, and no stale orders exist after redeploy (reset + sync)

## 3. Pi Admin version display

- [x] 3.1 Inject `APP_VERSION` / build time into pi-backend Docker image (mirror pi-frontend `pi-docker.yml` build args)
- [x] 3.2 Add Pi backend version to `GET /v1/health` or new `GET /v1/version` with tests
- [x] 3.3 Update `AdminHubView.vue` to show frontend label and backend label (fetch on mount)
- [x] 3.4 Add pi-frontend tests for version display (both present, backend unavailable fallback)

## 4. Pi connection setup (Option B)

- [x] 4.1 Add `probeApiBase()` utility (GET `/v1/setup/status` or `/v1/health`, distinguish network vs HTTP errors) with tests
- [x] 4.2 Add `ConnectionSetupView.vue` — URL field, test, save, **Use Play review demo** shortcut
- [x] 4.3 Add router route `/connection-setup` and startup guard in `App.vue` (before setup redirect when probe fails)
- [x] 4.4 Wire admin sync view to expose API base change if not already surfaced (reuse `saveApiBase` from `useSyncOperations`)
- [x] 4.5 Add frontend tests for probe logic, setup flow, demo shortcut URL, and saved-URL reuse

## 5. Android release fixes

- [x] 5.1 Remove erroneous `versionNameSuffix` from release build type in `android/app/build.gradle.kts`
- [x] 5.2 Confirm `versionCode` from `VERSION` is monotonic; add test or doc note if needed
- [x] 5.3 Update `android/README.md` with Play Store distribution and connection-setup behaviour

## 6. Android CI and Play upload

- [x] 6.1 Add `.github/workflows/android-release.yml` (JDK 17, Node 24, `bundleRelease`, artifact upload)
- [x] 6.2 Integrate keystore decode from secrets → `keystore.properties` in CI
- [x] 6.3 Add Play upload step via `r0adkll/upload-google-play-action` with `workflow_dispatch` track input (default: internal)
- [ ] 6.4 Manual verification: dispatch workflow, install from internal testing track, complete connection setup → demo → waiter login

## 7. Documentation and validation

- [x] 7.1 Add `docs/play-store.md` — operator checklist, secrets list, App access template, demo credentials placeholder
- [x] 7.2 Run full test suites and `./scripts/lint.sh` on feature branch
- [x] 7.3 Validate OpenSpec change: `npx openspec validate play-store-android-release --strict`
