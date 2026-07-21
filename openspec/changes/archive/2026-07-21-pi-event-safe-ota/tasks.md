## 1. Freeze signal (Pi backend + compose)

- [x] 1.1 Add failing tests for writing/clearing OTA freeze state from synced bundle event statuses (`prod` freezes; `test`-only clears)
- [x] 1.2 Implement OTA state dir writer (any synced event `prod` → freeze; otherwise clear) on bundle apply / startup
- [x] 1.3 Bind-mount host `ota-state` into `pi-backend` in `docker-compose.prod.yml` (and document path in deploy env)
- [x] 1.4 Run Pi backend tests for freeze writer

## 2. OTA script (minimize-outage + gates)

- [x] 2.1 Add `pi/deploy/pi-ota-update.sh` skeleton: respect freeze file, `FORCE_UPDATE`, logging
- [x] 2.2 Implement free-space gate (`OTA_MIN_FREE_BYTES` default **2 GiB**); on fail run dangling prune, re-check, then skip pull/apply without blacklisting if still low
- [x] 2.3 Implement pre-pull while containers keep running; no-op when digests unchanged
- [x] 2.4 Implement digest blacklist read/write with **no time expiry**; skip blacklisted digests; allow newer digests
- [x] 2.5 Implement **required** pre-apply health for new backend/frontend images via side containers (no live SQLite mount); on unhealthy image blacklist and keep old containers
- [x] 2.6 Implement short `compose up -d` apply, record previous digests, post-apply `/health` poll
- [x] 2.7 Implement rollback to previous digests on post-apply health failure + blacklist failed digests
- [x] 2.8 After successful post-apply health, run conservative dangling image prune; also prune on free-space-pressure path; never prune on freeze/blacklist-skip/health-failed apply; prune errors are non-fatal
- [x] 2.9 Add shell-level tests or a documented dry-run harness for freeze / free-space(+prune retry) / blacklist / required pre-apply / prune-guard paths where practical

## 3. Systemd and boot behavior

- [x] 3.1 Point `vendiqo-pi-update.service` at `pi-ota-update.sh` instead of raw `pull` + `up -d`
- [x] 3.2 Change `vendiqo-pi.service` to start from local images only (remove `ExecStartPre=pull`); keep `up -d`
- [x] 3.3 Keep delayed post-boot OTA at **`OnBootSec=5min`**; document it
- [x] 3.4 Update `install-vendiqo-pi.sh` / SD image hooks to install the script, create `ota-state`, and ship new units

## 4. Docs and operator escape hatch

- [x] 4.1 Document freeze, free-space gate (2 GiB + prune-on-pressure), required health checks, non-expiring blacklist, post-success prune, `FORCE_UPDATE`, and field upgrade steps in `pi/README.md` (and `docs/RELEASE.md` if needed)
- [x] 4.2 Note follow-ups explicitly out of scope: CI promote-to-`latest` soak

## 5. Verification

- [x] 5.1 Run Pi backend test suite
- [x] 5.2 Manually sanity-check script logic against freeze / free-space / blacklist / pre-apply scenarios (or CI-friendly script tests)
- [x] 5.3 Run `./scripts/lint.sh` for touched areas
