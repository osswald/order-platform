## Context

See proposal.md for motivation. Pi already has Admin → Betrieb tools (Testdruck, kitchen/pickup/display) via `useAdminOperations`, and open LAN order APIs (`POST /v1/orders`, settle-partial, payment receipt print, cash drawer on register cash settle). There is no generic job runner — only lifespan workers for print and sync. Event status (`config` | `test` | `prod` | `archive`) is on the synced bundle; `isEventTest` already exists in the Pi frontend. Bundle articles expose `additions[]` with optional `preselected`; there is no food/drink type on the edge bundle.

## Goals / Non-Goals

**Goals:**
- Backend-owned load-test job with HTTP start/status/stop and concurrent minute bursts
- Reuse real create → cash settle → optional receipt print paths so hardware side effects match production
- Admin UI under Betrieb with live progress polling
- Hard `test`-only enforcement at API (and UI gate)

**Non-Goals:**
- Persisting or resuming jobs across process restart
- Cleanup/purge UI or dedicated load-test purge
- SumUp/Twint/card settle paths
- Auto-printing kitchen monitor tickets
- Cloud admin surface or OpenAPI export for cloud frontend
- Generic reusable job framework beyond this feature

## Decisions

### 1. Job module + HTTP surface (not frontend timer)
**Choice:** In-process asyncio task with module-level status dict (same spirit as `sync_status`), started via `POST /v1/load-test/start`, polled via `GET /v1/load-test/status`, stopped via `POST /v1/load-test/stop`.  
**Why:** Survives leaving the admin page; matches “backend job, progress in frontend.”  
**Alternatives:** Frontend-only setInterval (fragile on sleep/navigation); durable job table (rejected — no persist required).

### 2. Invoke domain logic in-process, not HTTP-to-self
**Choice:** Call shared create/settle/receipt helpers (or router service functions) from the job with a DB session, rather than looping `httpx` to localhost.  
**Why:** Avoids auth/cookie noise, clearer error handling, easier tests. Concurrent actors still use separate sessions/tasks to simulate simultaneous posts.  
**Alternatives:** Self-HTTP (closer to real clients but noisier); raw ORM inserts (skips print/outbox — unacceptable).

### 3. Burst concurrency
**Choice:** Within each burst, `asyncio.gather` (or thread pool if sync SQLAlchemy blocks) one task per actor; SQLite may serialize writes — that still models “several waiters posted at once” contention. Cap outstanding burst work to configured actors only.  
**Why:** User asked to simulate simultaneous waiter posts.  
**Alternatives:** Strict serial creates (rejected).

### 4. Minute boundary
**Choice:** After a burst completes, sleep until `started_at + burst_index * 60s` (or remaining sleep to next minute wall). Do not start the next burst early if the previous burst overran; skip/catch up by starting immediately then aligning. Prefer: if burst took >60s, start next immediately and continue until total reached (document overrun).  
**Why:** Keeps ~1 order/actor/min under normal printer/DB load.

### 5. Actor and table assignment
**Choice:** Use the first W waiters and first R registers from event configuration (stable order by existing sort/name). Waiter tables cycle or random-uniform in `[table_min, table_max]`.  
**Why:** Deterministic actor pool; tables only matter for waiter create validation.

### 6. Basket generation
**Choice:** Build station → sellable non-addition article pools from `configuration.stations` + `articles`. Per order: pick `n ∈ [1, num_nonempty_stations]`, sample n stations, pick `people ∈ [1,8]`, for each person pick ≥1 article from those pools; merge identical lines. Additions: with probability ~0.5 if `additions` non-empty, sample `k ∈ [1, len]`, weighted by `preselected` (e.g. weight 3 vs 1). Skip stock-monitored articles that would fail; on create 409, count as failed and continue.  
**Why:** Matches locked product rules without inventing food/drink types.

### 7. Settle + receipt + drawer
**Choice:** After create, settle full remaining with a single cash `PaymentIn`; then with p=0.30 call the same path as `POST /v1/payments/{id}/receipt/print` targeting the register UUID when actor is register, else a suitable receipt station if available (skip print attempt if no target). Do not suppress cash drawer. Do not auto-print kitchen tickets.  
**Why:** Mirrors real UI (opt-in Beleg); drawer and station/pickup slips exercise hardware; kitchen stays manual.

### 8. Hard gate and single-flight
**Choice:** `start` reads cached bundle event status; non-`test` → 409. While running, each burst re-checks status and aborts if not `test`. Second `start` while `running`/`stopping` → 409. Stop sets a flag; current burst may finish in-flight actor tasks then exit.  
**Why:** Safety for real printers/Umsatz; one job is enough.

### 9. Frontend placement
**Choice:** New tile + route under `/admin/operations` (e.g. `admin-operations-load-test`), gated with `isEventTest(opsEvent.status)`. Form + Start/Stop; poll status ~1s while running. Reuse `useAdminOperations` event select.  
**Why:** Same pattern as Testdruck.

### 10. Addition weighting detail
**Choice:** Default attach probability 0.5 when additions exist; selection weights `preselected ? 3 : 1` without replacement until k picked. Not user-configurable in v1.  
**Why:** User asked for weighted additions; keep UI knobs to the four config values.

## Risks / Trade-offs

- **[SQLite write contention under gather]** → Actor tasks may serialize; still valid stress for app+print queue. If deadlocks appear, serialize DB writes inside a lock while keeping create requests logically concurrent.
- **[Burst overrun >60s under heavy print/DB]** → Next burst starts late or immediately after; effective rate drops below 1/actor/min — acceptable for a dry-run tool; surface `last_error` / slow bursts in status if useful.
- **[Stock 409s mid-run]** → Prefer non-monitored / in-stock articles; count failures; do not abort whole job on single failure.
- **[Cash drawer spam]** → Intentional; warn in UI copy that drawers will kick.
- **[Sync pushes synthetic Umsatz to cloud]** → Expected in `test`; test→prod purge remains the cleanup path (no in-tool purge).
- **[Process restart mid-run]** → Job state lost; printers may still have queued jobs — acceptable.

## Migration Plan

- Ship behind normal Pi deploy; no schema migration required if state is in-memory only.
- No cloud OpenAPI regeneration unless Pi OpenAPI is published (Pi PWA uses hand-typed paths today — keep that pattern).
- Rollback: remove routes/UI; no data migration.

## Open Questions

_(none — product decisions locked in exploration)_
