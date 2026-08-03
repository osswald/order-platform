## Why

Order and sync paths still rewrite the entire `SyncedBundle.json_body` (catalogue plus base64 logos) on every local stock mutation, which is the largest remaining SD-write cost on stocked events. Separately, after ETag/304 sync landed, `reapply_pending_stock` still runs on unchanged pulls: it re-decrements already-local stock and calls `save_bundle` every cycle while outbox backlog exists — amplifying wear and risking incorrect sellable counts.

## What Changes

- Persist local monitored stock outside the full organisation catalogue blob so FERTIG / stock mutations do **not** rewrite logos and catalogue JSON on SD
- Keep edge-visible sellable/`in_stock` behaviour equivalent: reads (and in-process cache) reflect cloud catalogue merged with local stock state
- Gate pending-outbox stock reapply so it runs only when the durable cloud catalogue baseline actually changed (real pull body), not on 304 / identical-body skips
- Skip durable stock persistence when reapply produces no stock-field changes
- Preserve restore and “fresh cloud body + pending outbox” correctness
- **Out of scope:** chunked cloud bundle pull; register-display debounce; print-job retention TTL; removing payload duplication across outbox/submissions; changing cloud stock APIs or OpenAPI; Redis

## Capabilities

### New Capabilities
- `pi-local-stock-overlay`: Durable local stock state for monitored articles/ingredients, merged into the effective organisation bundle without rewriting the full catalogue `json_body` on every stock mutation

### Modified Capabilities
- `pi-sync-cycle-efficiency`: Pending-outbox stock reapply and any stock persistence that follows a pull MUST NOT run on no-op pulls (304 / identical body); reapply remains required after a real catalogue baseline change
- `pi-bundle-in-process-cache`: Cache coherence after stock mutation MUST hold when stock is persisted via the overlay path (not only when `SyncedBundle.json_body` is rewritten)

## Impact

- **Pi backend**: `stock.py` (`save_bundle` / apply path), `bundle_cache.py`, `sync_service.reapply_pending_stock` / `pull_and_restore`, `edge_orders` order-create stock path, `operational_restore` stock reapply, new Alembic revision after `008_hot_path_indexes`, models + tests
- **APIs / OpenAPI**: none (effective bundle shape for clients unchanged)
- **Ops**: one-time migration; smaller, more frequent stock-row writes instead of multi‑MB TEXT rewrites on order path
- **Related**: builds on in-process bundle cache and sync-cycle ETag work; complements (does not replace) hot-path indexes
