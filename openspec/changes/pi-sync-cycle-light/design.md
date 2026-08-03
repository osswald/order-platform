## Context

See proposal.md for motivation. Today `cloud_client.py` opens `async with httpx.AsyncClient(...)` on every helper (`fetch_bundle`, `fetch_operational_snapshot`, `submit_operational_chunk`, …). `pull_and_restore` always GETs the full bundle, always `json.dumps` + SQLite write, always clears the logo cache, then always GETs the operational snapshot (if restore enabled) and fingerprints all open orders. `fetch_bundle_manifest` / `fetch_bundle_chunk` exist only on the Pi client — cloud has no matching routes.

Constraints:
- Preserve outbox ack/error semantics and `pi-operational-restore` correctness when a check runs
- Keep `sync_cycle_lock` for SQLite writer safety
- No cloud OpenAPI / edge route changes in this change
- Receipt logo cache clear remains tied to **actual** bundle body changes (from `pi-receipt-render-offload`)

## Goals / Non-Goals

**Goals:**
- One `httpx.AsyncClient` per sync cycle for edge calls used by that cycle
- No-op pull when body unchanged (no SQLite write, no logo-cache clear)
- Debounced snapshot/restore evaluation while idle
- Observable via tests (mock transport / call counts)

**Non-Goals:**
- Cloud-side bundle manifest/ETag/chunk APIs
- In-process POS `get_bundle_dict` cache (slice B)
- Print-worker wake/idle changes (D)
- Removing `sync_cycle_lock` or overlapping concurrent pull+push
- Changing SumUp / unpair / health client patterns beyond optional later reuse (focus: sync cycle path)

## Decisions

### 1. Cycle-scoped shared client via context / parameter

**Choice:** Introduce an internal helper (e.g. `cloud_request_session` or `async with edge_http_client() as client`) used by `run_sync_cycle` / `pull_and_restore` / `push_outbox`. Low-level functions accept an optional `client: httpx.AsyncClient | None`; if omitted, create a short-lived client (preserve one-off callers like SumUp).

**Alternatives considered:**
- Process-lifetime singleton client — harder to reset on credential rewrite / base URL change; connection reuse across minutes is nice but cycle-scoped is enough
- Only reuse within `push_outbox` — misses pull+snapshot savings

### 2. Bundle identity = exact stored `json_body` string compare (or hash)

**Choice:** After `fetch_bundle()`, compare downloaded serialization to `SyncedBundle.json_body`. Prefer hashing both sides (`sha256`) if bodies are large, or direct equality if already strings. On match: return existing parsed dict (or `json.loads` once) without UPDATE. On mismatch: write as today + `clear_receipt_logo_cache()`.

**Caveat:** Cloud may re-serialize with key order differences even when semantically identical — that still counts as “changed” and is acceptable (rare; still correct). Do not invent canonicalization in v1.

**Alternatives considered:**
- Semantic deep equality — expensive and brittle
- Cloud ETag — requires cloud work (follow-up)

### 3. Restore-check debounce state in module-level sync status

**Choice:** Track `last_restore_check_at` (and maybe `last_restore_check_bundle_hash`) on `sync_status` / module vars. Helper `should_check_operational_restore(db, *, bundle_changed: bool) -> bool` implements:

```
if not restore_enabled: return False
if never_checked_this_process: return True
if bundle_changed: return True
if pending_outbox_count > 0: return True
if now - last_restore_check_at >= RESTORE_CHECK_MAX_IDLE_SECONDS: return True
return False
```

Default max idle: **300s** (5 minutes), overridable via env `SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (min clamp e.g. ≥ sync interval).

**Rationale:** Multi-Pi takeover / cloud-open-order appearance while local is idle still converges within 5 minutes without hammering snapshot every 60s.

**Alternatives considered:**
- Skip snapshot entirely when outbox empty — too weak for takeover
- Only check when bundle changes — misses pure operational drift with static catalog

### 4. Chunked bundle pull deferred

**Choice:** Document as follow-up; do not call non-existent cloud routes. Leave `fetch_bundle_manifest` / `fetch_bundle_chunk` unused until cloud implements them.

### 5. Lock scope unchanged

**Choice:** Keep holding `sync_cycle_lock` for the whole cycle. Wins come from less work inside the lock, not from overlapping cycles.

## Risks / Trade-offs

- **[Delayed detection of cloud-only open-order drift]** → Max idle interval caps lag; pending outbox and bundle change still force immediate check.
- **[Semantically identical but reordered JSON still rewrites]** → Acceptable; no silent stock/logo bugs.
- **[Shared client + credential rotation mid-cycle]** → Rare; cycle uses credentials resolved at start; next cycle picks up new edge.env.
- **[Tests assuming snapshot every cycle]** → Update restore/sync tests to assert debounce + force paths.

## Migration Plan

- Pi-only deploy. New env var optional (defaults apply).
- Rollback = revert Pi backend; no DB migration.

## Open Questions

- Exact default for `SYNC_RESTORE_CHECK_MAX_IDLE_SECONDS` (propose 300; confirm if venues need faster multi-Pi takeover).
- Whether manual `POST /v1/sync/pull` should always force a restore check (recommend **yes**).
