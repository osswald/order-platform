## 1. Probe timeout and Demo label (Pi frontend)

- [x] 1.1 Add/extend `probeApiBase` tests for AbortSignal timeout (~2500 ms) mapping to `reason: 'network'`
- [x] 1.2 Implement probe timeout in `pi/frontend/src/utils/probeApiBase.ts`
- [x] 1.3 Update `ConnectionSetupView` tests for button label **Demo**
- [x] 1.4 Rename connection-setup button copy to **Demo** (URL constant unchanged)
- [x] 1.5 Run Pi frontend tests for probe + connection setup

## 2. Play-review deploy hardening

- [x] 2.1 Update `scripts/deploy-play-review.sh` to require JSON `/health` (reject HTML) and assert CORS for `Origin: https://appassets.androidplatform.net`
- [x] 2.2 Align `docs/play-store.md` / `cloud/play-review/README.md` troubleshooting and reviewer instructions with **Demo** label, `/health` JSON expectation, and scheduled cleanup
- [x] 2.3 Remove or narrow compose healthcheck comments that treat SPA `/health` as acceptable long-term (optional cleanup if still misleading)

## 3. Scheduled test→prod-style cleanup

- [x] 3.1 Extend Pi `purge_event_local_data` (and tests) so test→prod purge also deletes `emulated_receipts`
- [x] 3.2 Add a play-review cleanup entry point that runs cloud `purge_event_operational_data` for the demo event and triggers Pi `purge_event_local_data` (without status change)
- [x] 3.3 Wire a daily schedule (workflow or cron) and document cadence in operator docs
- [x] 3.4 Add/adjust tests proving cleanup clears orders + emulated receipts and leaves pairing/status intact

## 4. Verify and ship ops fix

- [x] 4.1 Confirm published `pi-frontend-amd64-latest` includes nginx `location /health` proxy (rebuild/publish from `main` if not)
- [ ] 4.2 Redeploy play-review on VPS (`./scripts/deploy-play-review.sh` or workflow) and verify public `/health` JSON + CORS
- [ ] 4.3 Smoke-test Android internal build: Demo button → connection OK → save → waiter login
- [ ] 4.4 Manually or via schedule dry-run: confirm orders/emulated receipts cleared after cleanup

## 5. Wrap-up

- [x] 5.1 Run `./scripts/lint.sh` on touched areas / full as appropriate
- [x] 5.2 Open PR from feature branch; note that ops `/health` fix unblocks existing APKs, timeout/label need new Android release
