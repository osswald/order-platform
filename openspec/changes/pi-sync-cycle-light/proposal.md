## Why

Every Pi sync cycle (~60s) opens a new `httpx.AsyncClient` for the full bundle GET, another for the operational snapshot, and one more per outbox chunk — then always writes the bundle to SQLite and fingerprints open orders even when nothing changed. That burns CPU, network, and SD writes on the appliance and holds `sync_cycle_lock` longer than necessary, competing with print worker and reachability probes.

## What Changes

- Reuse one shared `httpx.AsyncClient` for all cloud calls within a sync cycle (bundle, snapshot, outbox pushes)
- Skip rewriting `SyncedBundle` / logo-cache invalidation when the pulled bundle body is byte-identical to the stored body
- Debounce operational-snapshot fetch + restore fingerprinting: still run on bundle change, pending/error outbox, startup/first cycle, and at a configurable max interval; skip the redundant middle cycles when idle
- Keep `sync_cycle_lock` for SQLite safety; shorten critical work by avoiding no-op writes and unnecessary snapshot HTTP
- **Out of scope:** implementing cloud `GET /edge/v1/bundle/manifest` + chunk pull (Pi client stubs exist; cloud endpoints do not) — track as a follow-up once cloud can serve incremental bundles

## Capabilities

### New Capabilities
- `pi-sync-cycle-efficiency`: Lighter Pi↔cloud sync cycles — shared HTTP client, skip-identical bundle writes, debounced operational restore checks

### Modified Capabilities
- _(none — `pi-operational-restore` correctness requirements stay binding; restore still runs when fingerprints diverge, just not on every idle tick)_

## Impact

- **Pi backend**: `cloud_client.py`, `sync_service.py`, `sync_worker.py`, tests under `pi/backend/tests/` (sync / restore)
- **Env**: optional `SYNC_RESTORE_CHECK_INTERVAL_SECONDS` (or similar) for max time between restore checks when idle
- **Cloud**: no API changes in this change
- **Out of scope**: in-process organisation bundle cache for POS requests (slice B), print-worker idle tuning (D), SQLite index migrations (A), chunked bundle pull (needs cloud)
