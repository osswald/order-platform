## 1. Shared HTTP client for sync cycle

- [x] 1.1 Add failing tests that a sync cycle with multiple outbox pushes (and pull) uses one `httpx.AsyncClient` instance (mock transport / call instrumentation)
- [x] 1.2 Refactor `cloud_client` edge helpers used by sync (`fetch_bundle`, `fetch_operational_snapshot`, `submit_operational_chunk`, fallback `submit_order`) to accept an optional shared client
- [x] 1.3 Wire `run_sync_cycle` / `pull_and_restore` / `push_outbox` to open one client per cycle and pass it through

## 2. Cloud conditional bundle and snapshot (ETag)

- [x] 2.1 Add failing cloud tests: bundle/snapshot return `ETag`; matching `If-None-Match` → 304 without full body; content change → 200 + new ETag
- [x] 2.2 Implement canonical JSON + sha256 ETag on `GET /edge/v1/bundle` and honour `If-None-Match`
- [x] 2.3 Implement the same for `GET /edge/v1/sync/operational/snapshot` (respect `event_id` scope)
- [x] 2.4 Export OpenAPI / regenerate cloud frontend API types if required by repo conventions for this change

## 3. Pi conditional pull + skip identical writes

- [x] 3.1 Add failing Pi tests: 304 skips `SyncedBundle` rewrite and logo-cache clear; 200 with new body writes + clears; no-ETag fallback uses body hash
- [x] 3.2 Persist bundle ETag (Alembic/schema patch on `synced_bundle` or equivalent) and send `If-None-Match` from `fetch_bundle`
- [x] 3.3 Handle 304 vs 200 in `pull_bundle`; only `clear_receipt_logo_cache` when body actually changes
- [x] 3.4 Store snapshot validator in process/`sync_status`; on snapshot 304 skip restore fingerprint/apply but mark check completed

## 4. Debounced operational restore checks

- [x] 4.1 Add failing tests for: idle skip within max interval; force on bundle change; force on pending/error outbox; force when max idle exceeded; force on first check / manual pull
- [x] 4.2 Implement `should_check_operational_restore` + `SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (default 300)
- [x] 4.3 Integrate into `pull_and_restore`; manual sync/pull always forces a restore check
- [x] 4.4 Confirm restore path still satisfies `pi-operational-restore` when snapshot is 200 and fingerprints diverge

## 5. Verification

- [x] 5.1 Run cloud backend tests for edge bundle/snapshot conditional behaviour
- [x] 5.2 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [x] 5.3 Run `./scripts/lint.sh --staged` (or full) before commit
