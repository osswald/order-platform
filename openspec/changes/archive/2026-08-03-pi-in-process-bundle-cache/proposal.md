## Why

Every Pi edge request that needs catalogue/config still hits SQLite and `json.loads` the full `SyncedBundle` — including base64 receipt logos — even though the module is named `bundle_cache`. Order submit loads it twice in one FERTIG path. That repeated parse is now one of the largest remaining CPU costs on the money path after logo raster caching and deferred ESC/POS render landed.

## What Changes

- Keep a process-memory organisation bundle after the first successful load (or after a mutating write updates it)
- Serve `get_bundle_dict` / `get_bundle_dict_raw` from that cache on subsequent reads within the same process
- Invalidate or replace the cache whenever the persisted bundle body changes: successful sync pull with a new body, `save_bundle` (stock), operational restore that rewrites the bundle, and any other writers of `SyncedBundle.json_body`
- Stay coherent with existing receipt-logo raster invalidation and sync 304 / skip-identical-write behaviour (do not clear or thrash caches on no-op pulls)
- Callers keep the same function API; no HTTP contract changes
- **Out of scope:** Redis or other external cache; eliminating full-bundle `save_bundle` SD rewrites; chunked bundle pull; print-worker wake tuning; SQLite index migrations

## Capabilities

### New Capabilities
- `pi-bundle-in-process-cache`: Process-memory organisation bundle for Pi edge reads, with correct invalidation on real body changes

### Modified Capabilities
- _(none — `pi-sync-cycle-efficiency` and `pi-receipt-render-offload` stay binding; this change must not regress their skip/clear rules)_

## Impact

- **Pi backend**: primarily `bundle_cache.py`, `stock.save_bundle`, sync pull / restore writers; ~50+ call sites keep using `get_bundle_dict*` unchanged
- **APIs / OpenAPI**: none (behavioural performance + correctness of freshness only)
- **Memory**: one in-process copy of the organisation bundle (size tracks current SQLite `json_body`)
- **Deploy**: Pi-only; restart clears cache (cold first request reloads from SQLite as today)
- **Related**: complements `pi-sync-cycle-efficiency` (fewer SD rewrites) and `pi-receipt-render-offload` (logo rasters); does not replace them
