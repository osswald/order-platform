## 1. Shared HTTP client for sync cycle

- [ ] 1.1 Add failing tests that a sync cycle with multiple outbox pushes (and pull) uses one `httpx.AsyncClient` instance (mock transport / call instrumentation)
- [ ] 1.2 Refactor `cloud_client` edge helpers used by sync (`fetch_bundle`, `fetch_operational_snapshot`, `submit_operational_chunk`, fallback `submit_order`) to accept an optional shared client
- [ ] 1.3 Wire `run_sync_cycle` / `pull_and_restore` / `push_outbox` to open one client per cycle and pass it through

## 2. Skip identical bundle writes

- [ ] 2.1 Add failing tests: unchanged bundle body does not UPDATE `SyncedBundle` and does not clear logo cache; changed body still writes and clears
- [ ] 2.2 Implement pull compare (hash or exact `json_body`) and conditional write / `clear_receipt_logo_cache`
- [ ] 2.3 Return parsed bundle to callers without forcing a redundant round-trip when unchanged

## 3. Debounced operational restore checks

- [ ] 3.1 Add failing tests for: idle skip within max interval; force on bundle change; force on pending/error outbox; force when max idle exceeded; force on first check / manual pull
- [ ] 3.2 Implement `should_check_operational_restore` + `SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (default 300)
- [ ] 3.3 Integrate into `pull_and_restore`; ensure manual sync/pull path always forces a restore check
- [ ] 3.4 Confirm restore path still satisfies `pi-operational-restore` when a check runs (existing restore tests remain green)

## 4. Verification

- [ ] 4.1 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [ ] 4.2 Run `./scripts/lint.sh --staged` (or full) before commit
