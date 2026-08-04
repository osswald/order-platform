## Context

See proposal.md for motivation. Print worker (`print_worker.py`) polls every 1s with a sync `SessionLocal`, calls sync `ensure_print_job_payload` on the asyncio loop, then async TCP send. Enqueue sites: `edge_common` (station/kitchen/pickup/voucher/payment_receipt/cash_drawer), `edge_kitchen`, `edge_print_jobs` retry, shift close. Alembic head is `007_synced_bundle_etag`; many ORM `index=True` columns never shipped as migrations—`create_all` in tests has them, migrated Pis often do not. `pi-receipt-render-offload` already deferred HTTP-path ESC/POS into the worker.

## Goals / Non-Goals

**Goals:**
- Wake signal from enqueue/retry into `print_worker_loop`
- Off-loop render for deferred payload build
- Alembic `008_*` (+ ORM align) for hot filters
- Tests for wake latency, non-blocking render (or thread offload), and index presence

**Non-Goals:**
- Changing PrintJob kinds or HTTP APIs
- Moving TCP send off-loop (already async)
- Full ORM/Alembic audit of every historical `index=True`
- Multi-process Redis wake bus

## Decisions

### 1. Wake via `asyncio.Event` (module-level)

**Choice:** `print_jobs_wakeup: asyncio.Event` cleared at start of each wait; enqueue/retry helpers call `notify_print_worker()` after the job is durable (`flush`/`commit` as appropriate). Loop: `await wait_for(wakeup.wait() or stop, timeout=IDLE_TIMEOUT)` with IDLE_TIMEOUT default **1–5s** (keep ≤5s so missed wakes recover quickly; may raise above 1s once wake exists).

**Alternatives:** Always 1s poll only — status quo. `asyncio.Queue` of job ids — duplicates durable queue, harder on crash.

### 2. Off-loop render with `asyncio.to_thread`

**Choice:** In `process_print_job` / worker loop, run `ensure_print_job_payload(db_or_detached_context)` via `asyncio.to_thread`. Prefer: load job + render_context (and any ORM fields needed) on the loop session, pass plain data into thread-safe render that returns payload bytes, then write payload back on the loop session—**do not share SQLAlchemy Session across threads**.

**Alternatives:** Process pool — heavier. Keep sync render — continues to stall HTTP under load.

### 3. Notify coverage

**Choice:** Central helper used by `_create_print_job_for_lines` / deferred creators and `retry_print_job`. Audit shift/cash_drawer paths that insert `queued` jobs. Safe no-op if loop not started yet (Event set is fine; next loop iteration sees queued rows).

### 4. Index set (minimum)

**Choice:** New revision `008_hot_path_indexes` down_revision `007_synced_bundle_etag`:

| Index | Columns |
|-------|---------|
| `ix_print_jobs_status` | `print_jobs.status` |
| `ix_order_submissions_event_payment` | `(event_id, payment_status)` |
| `ix_sync_outbox_status` | `sync_outbox.status` |
| `ix_kitchen_tickets_event_status` | `(event_id, status)` |

Add matching `index=True` / `Index(...)` on models. Optional: `ix_sync_outbox_event_status` if profiles show composite wins—start with status alone if write amplification is a concern.

**Alternatives:** Only `print_jobs.status` — incomplete for lists/sync. Giant covering indexes — defer.

### 5. Schema patch fallback

**Choice:** Follow existing Pi pattern: Alembic upgrade + optional `_add_index_if_missing` in `database.py` for appliances that fall back to patches when Alembic fails in non-prod—or rely on Alembic only if patches are index-awkward on SQLite. Prefer Alembic + ORM align; add patch helpers if other columns already use `_add_column_if_missing` for drift.

## Risks / Trade-offs

- **[Session used in worker thread]** → Pass detached/plain context only; mutate DB on loop thread.
- **[Wake before commit visible]** → Notify after commit (or after flush in same connection the worker will see—prefer after request commit for HTTP paths).
- **[Index build time on large DBs]** → Accept one-time migrate cost; SQLite locks briefly.
- **[Spurious wakes]** → Cheap; drain up to N jobs then wait again.
- **[to_thread GIL]** → Pillow releases GIL often enough for benefit on ARM; still removes event-loop stall.

## Migration Plan

1. Deploy Pi image with `008` + worker changes together (indexes help the still-polled/woken worker).
2. Rollback worker code independently if needed; indexes are additive and safe to keep.
3. No cloud/OpenAPI changes.

## Open Questions

- Exact idle timeout default once wake lands (recommend **2s** fallback).
- Whether cash-drawer / shift prebuilt jobs need notify (yes if they use `queued` + worker send).
