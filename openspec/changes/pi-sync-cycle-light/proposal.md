## Why

Every Pi sync cycle (~60s) opens a new `httpx.AsyncClient` for the full bundle GET, another for the operational snapshot, and one more per outbox chunk — then always downloads and writes the bundle and fingerprints open orders even when nothing changed. That burns CPU, network, and SD writes on the appliance and holds `sync_cycle_lock` longer than necessary, competing with print worker and reachability probes. Local body-compare alone still forces a full download; cloud conditional responses (ETag / `If-None-Match`) avoid that.

## What Changes

- Reuse one shared `httpx.AsyncClient` for all cloud calls within a sync cycle (bundle, snapshot, outbox pushes)
- **Cloud:** emit a stable `ETag` (or equivalent version token) on `GET /edge/v1/bundle` and `GET /edge/v1/sync/operational/snapshot`; honour `If-None-Match` with **304 Not Modified** when unchanged
- **Pi:** send stored validators on pull/snapshot; on 304 skip body download, SQLite rewrite, and logo-cache invalidation; treat snapshot 304 as “cloud operational state unchanged” (skip restore fingerprint work for that check)
- Keep a local body-hash fallback when cloud omits validators (older cloud / misconfig) so Pi-only savings still apply
- Debounce operational-snapshot fetch when idle (bundle/validators unchanged, empty outbox, within max idle interval); force on startup, manual pull, pending outbox, bundle change, or max idle
- Keep `sync_cycle_lock` for SQLite safety; shorten work inside the lock via 304s and no-op writes
- **Out of scope:** full `bundle/manifest` + chunked section pull (separate, larger change)

## Capabilities

### New Capabilities
- `pi-sync-cycle-efficiency`: Lighter Pi↔cloud sync — shared HTTP client, conditional bundle/snapshot (ETag), skip-identical local writes, debounced restore checks

### Modified Capabilities
- _(none — `pi-operational-restore` correctness stays binding when a restore check runs and cloud state may have changed)_

## Impact

- **Cloud backend**: `edge` bundle + operational snapshot routes; stable ETag/version derivation; OpenAPI export + cloud frontend type regen if headers/schemas are documented
- **Pi backend**: `cloud_client.py`, `sync_service.py`, `sync_worker.py`; persist last bundle/snapshot validators (column or side meta); tests on both sides
- **Env**: optional `SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (default 300)
- **Deploy**: prefer cloud with ETag before or with Pi; old Pis ignore validators; new Pis fall back to full GET + local compare if cloud has no ETag
- **Out of scope**: in-process POS `get_bundle_dict` cache, print-worker idle tuning, SQLite index migrations, chunked bundle pull
