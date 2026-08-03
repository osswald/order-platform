## Context

See proposal.md for motivation. Today `cloud_client.py` opens a new `httpx.AsyncClient` per helper; `pull_and_restore` always GETs the full bundle, always writes SQLite, always clears the logo cache, then always GETs the operational snapshot (if restore enabled) and fingerprints open orders. Cloud `GET /edge/v1/bundle` and `GET /edge/v1/sync/operational/snapshot` always return full JSON with no validators. Pi stubs for bundle manifest/chunk remain unused (cloud has no those routes).

Constraints:
- Preserve outbox ack/error semantics and `pi-operational-restore` when cloud operational state may have changed
- Keep `sync_cycle_lock` for SQLite writer safety
- Receipt logo cache clear only on **actual** bundle body changes
- Old Pis / new cloud and new Pis / old cloud must interoperate (fallback paths)
- OpenAPI sync for cloud schema/header documentation when required by repo conventions

## Goals / Non-Goals

**Goals:**
- One `httpx.AsyncClient` per sync cycle
- Cloud ETag (or equivalent) + `If-None-Match` → 304 on unchanged bundle and snapshot
- Pi persists validators; 304 skips download side-effects; local body-hash fallback without validators
- Debounced snapshot fetch while idle; snapshot 304 skips restore fingerprint/apply
- Tests on cloud and Pi

**Non-Goals:**
- Full bundle manifest + chunked section pull
- In-process POS `get_bundle_dict` cache (explore slice B)
- Print-worker wake/idle (D)
- Removing `sync_cycle_lock` / overlapping pull+push
- Changing SumUp / unpair / health beyond optional later client reuse

## Decisions

### 1. Cycle-scoped shared client via context / parameter

**Choice:** Sync-path helpers accept optional `httpx.AsyncClient`; `run_sync_cycle` opens one client for the cycle. One-off callers (SumUp, unpair) keep short-lived clients.

**Alternatives considered:** Process-lifetime singleton — credential/base URL rotation is messier; cycle-scoped is enough.

### 2. Cloud validators = strong content ETag from canonical bytes

**Choice:** After assembling the bundle (or snapshot) dict, serialize to a **canonical JSON** form (sorted keys, compact separators) and set `ETag` to `"<sha256-hex>"` (quoted strong ETag). Honour `If-None-Match` including weak/strong common client forms; on match return 304 with empty body.

**Why hash assembled payload:** No existing org-level revision counter; hashing matches what the Pi would store. Cache the last `(org_id, etag, assembled_at)` in-process on cloud if assemble+hash is hot — optional optimization, not required for correctness.

**Alternatives considered:**
- `max(updated_at)` across tables — incomplete (misses nested config edits unless every path bumps timestamps)
- Opaque revision table — cleaner long-term, more migration work; defer
- Weak ETags only — fine, but strong hash is simple and precise

**Snapshot scope:** Hash the JSON for the same filtered event set the handler returns (org-wide or `event_id` query). Validator is per request scope.

### 3. Pi stores validators next to sync state

**Choice:** Persist last bundle ETag on the Pi (prefer new nullable column on `synced_bundle`, e.g. `etag`, plus optional `snapshot_etag` in sync module state or a tiny `sync_meta` row). Send as `If-None-Match` on GET. On 200, update validator from response header. On 304, leave body and logo cache alone.

**Local fallback:** If 200 and no ETag, compare downloaded serialization to `json_body` (sha256) before write/clear.

### 4. Snapshot 304 short-circuits restore

**Choice:** 304 ⇒ cloud open-state unchanged ⇒ skip `needs_operational_restore` / restore apply; still update `last_restore_check_at`.

**Rationale:** Fingerprinting all local open orders is wasted when cloud already said nothing moved.

### 5. Restore-check debounce (still useful with ETag)

**Choice:** Keep debounce so idle cycles often skip the snapshot HTTP entirely (even a cheap 304 has RTT). Force check when: never checked; bundle changed; pending/error outbox; manual pull; `now - last >= SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (default **300**).

Manual `POST /v1/sync/pull` (and equivalent manual sync) **always** forces a restore check.

### 6. Chunked pull still deferred

**Choice:** Leave `fetch_bundle_manifest` / `fetch_bundle_chunk` unused; do not implement cloud chunk routes in this change.

### 7. Lock scope unchanged

**Choice:** Hold `sync_cycle_lock` for the whole cycle; reduce work inside it.

## Risks / Trade-offs

- **[Canonical JSON drift between cloud hash and Pi fallback compare]** → ETag path uses cloud-only canonicalization; Pi fallback compares raw stored body to downloaded `response.text` / re-serialized client JSON carefully (prefer compare to response body bytes as received).
- **[Stale ETag if assemble omits a field that changed]** → Hash full response payload; any missed mutate path still changes bytes when reflected in bundle.
- **[Deploy skew]** → Pi without cloud ETag: full GET + local compare. Cloud without Pi support: headers ignored by old clients.
- **[Delayed multi-Pi operational drift]** → Debounce + max idle; 304 does not extend beyond max idle forced checks.
- **[Hash CPU on cloud]** → Acceptable vs shipping full JSON; add per-org etag memo later if profiles hurt.

## Migration Plan

1. Ship cloud ETag support (backward compatible).
2. Ship Pi conditional client + `etag` column migration / schema patch.
3. Regenerate/export OpenAPI if the project documents response headers or related schemas.
4. Rollback either side independently; validators are additive.

## Open Questions

- Whether to memoize cloud ETag per org in Redis/memory in v1 or hash every request (recommend **hash every request** first; memoize only if needed).
- Persist snapshot ETag in SQLite vs process memory (recommend **process memory + sync_status** for snapshot; **SQLite column** for bundle so restarts still 304).
