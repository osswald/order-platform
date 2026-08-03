## Context

See proposal.md for motivation. Today `bundle_cache.py` always queries `SyncedBundle` and `json.loads` the full `json_body`. Call sites (~50+) go through `get_bundle_dict` / `get_bundle_dict_raw`; `POST /v1/orders` loads twice per submit before `save_bundle`. Durable writers: `stock.save_bundle`, sync `pull_bundle` (on real body change), restore/stock reapply paths that call `save_bundle`. Sync 304 / identical-body skip and `clear_receipt_logo_cache` already distinguish real body change vs no-op (see `pi-sync-cycle-efficiency` / `pi-receipt-render-offload`).

Constraints:
- Single Pi backend process (no Redis / multi-worker shared cache required)
- SQLite remains source of truth; process memory is an accelerator
- Must not regress stock freshness after FERTIG or after a real sync pull
- Avoid clearing logo raster cache on no-op pulls (already gated on body change)

## Goals / Non-Goals

**Goals:**
- Process-memory hit for warm `get_bundle_dict*` reads
- Single invalidate/update chokepoint on durable body writers
- Preserve helper error/`None` semantics
- Tests proving skip-parse on warm read + freshness after `save_bundle` / changed pull

**Non-Goals:**
- External cache (Redis, etc.)
- Stopping full-bundle `json.dumps` on every stock save (possible later)
- Deduplicating the two loads inside `create_local_order` by refactoring that handler alone (nice follow-up; cache makes the second load cheap even without that)
- Print-worker wake, SQLite indexes, chunked bundle

## Decisions

### 1. Module-level cache inside `bundle_cache.py`

**Choice:** Hold `_cached_bundle: dict | None` (and optionally a generation / content fingerprint) in `bundle_cache.py`. `get_bundle_dict` / `get_bundle_dict_raw` populate on miss; export `invalidate_bundle_cache()` and/or `set_bundle_cache(data)` for writers.

**Alternatives considered:** Per-request FastAPI dependency cache — doesn’t help across requests. Redis — ops/RAM cost with no multi-process need.

### 2. Return policy: copy on read vs shared mutable dict

**Choice:** On cache hit, return a **shallow copy** of the top-level dict by default is insufficient for nested stock mutation; prefer **`copy.deepcopy` on read** *or* document that callers that mutate must own a deep copy and that `save_bundle` always takes the mutated object and writes through `set_bundle_cache`.

**Practical pick for this codebase:** Many callers mutate nested `events[].articles` then `save_bundle(db, bundle)`. If the cache returns the **same** object, mutation is visible in-process before save (usually fine) but concurrent requests could see half-applied stock. Pi is effectively single-threaded asyncio for sync handlers, but still safer to:

- **`save_bundle`**: after persist, `set_bundle_cache(deepcopy(bundle))` (or store the saved object as the new cache).
- **Reads**: return `deepcopy(_cached)` so accidental mutation doesn’t corrupt the cache until an explicit save.

**Alternatives:** Shared reference + discipline — faster, easier to footgun. Deepcopy-on-read costs CPU but still far cheaper than `json.loads` of a logo-heavy body on ARM.

### 3. Writer chokepoint = `save_bundle` + sync pull apply path

**Choice:** Update cache inside `save_bundle` (covers stock, restore reapply, anything already using it). Sync `pull_bundle` on real body change either calls `save_bundle`-equivalent update or `set_bundle_cache` / `invalidate` after commit. On 304 / identical skip, leave cache alone (or refresh from existing row only if empty).

**Do not** invalidate solely because `clear_receipt_logo_cache` ran — logo clear already runs only on body change; keep that coupling one-way: body change → update bundle cache **and** clear logos (existing).

### 4. No API / OpenAPI changes

**Choice:** Behavioural only; same HTTP responses.

### 5. Test strategy

**Choice:** Unit tests in Pi backend that instrument/monkeypatch `json.loads` or count SQLite/query parses: warm second `get_bundle_dict` does not re-parse; after `save_bundle` with mutated stock, next get sees new values; after invalidate/empty, miss reloads; strict vs raw error/`None` unchanged. Optional: order-submit path still ends with correct stock in subsequent get.

## Risks / Trade-offs

- **[Stale cache after a writer forgets to update]** → Centralise on `save_bundle` + sync apply; grep for direct `SyncedBundle.json_body =` assignments and route them through the helper.
- **[Deepcopy cost on every read]** → Still typically cheaper than JSON parse of logo-bearing payloads; measure if needed; can switch to copy-on-write later.
- **[Memory]** → One bundle-sized object; acceptable on appliance; restart clears.
- **[Tests sharing process state]** → Reset/invalidate cache in fixtures or at test start to avoid cross-test bleed.

## Migration Plan

1. Land Pi-only change behind existing helpers (no flag required).
2. Rollback = revert deploy; SQLite path remains correct.
3. No schema migration.

## Open Questions

- Whether to also pass the already-loaded bundle through `create_local_order` to avoid the second logical load entirely (optional micro-optimisation once cache exists).
