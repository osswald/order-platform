## Context

See `proposal.md` for motivation. After `cloud-busy-event-reporting`, stats/dashboard/transactions no longer full-scan by default, but collective bills still do:

```
build_event_collective_bills_list
  └─ EdgeSubmittedOrder WHERE event_id = ?  → .all()
       └─ Python: keep rows with payload.collective_bill_uuid

_maybe_close_collective_bill
  └─ same full-event .all() + filter by UUID

build_single_collective_bill
  └─ build_event_collective_bills_list(entire event) → pick one UUID
```

`EventCollectiveBill` headers already exist and are indexed by `event_id` / `uuid`. Order membership lives only inside JSON `payload`. Transactions already use JSON path filters for `payment_status` (`payload["payment_status"].as_string()`); collective-bill UUID has no index and list builders still prefer Python scans.

## Goals / Non-Goals

**Goals:**
- SQL filter for “orders on this event with a collective bill” and “orders for bill UUID X”
- Close detection and single-bill PDF use narrowed queries
- Ingest + backfill keep filters trustworthy
- Stable admin/PDF JSON contracts

**Non-Goals:**
- Background PDF workers
- Replacing line/payment formatting with `EdgeOrderItem` aggregates in this change (payload remains detail source after the narrowed set is loaded)
- Pi protocol or frontend redesign
- Expression-index-only approach without a clear backfill/ingest story if it fails on SQLite test DB — prefer portable denormalized columns

## Decisions

### 1. Denormalize membership columns on `EdgeSubmittedOrder`

Add nullable indexed columns, at minimum:

- `collective_bill_uuid: String(36) | None` — copied from `payload["collective_bill_uuid"]` when present
- Optionally `payment_status: String(...) | None` — copied from payload for close detection without JSON extraction (nice-to-have if it simplifies `_maybe_close_collective_bill`; otherwise JSON path on the already-filtered bill rows is enough)

Composite index: `(event_id, collective_bill_uuid)` (partial index `WHERE collective_bill_uuid IS NOT NULL` if the DB/migration style supports it cleanly).

**Why not JSON expression index only?** Works on PostgreSQL but is awkward under the project’s SQLite test suite and harder to keep consistent with ORM filters. Denormalized columns match existing explicit columns (`event_id`, `organisation_id`) and are easy to set at ingest.

**Alternatives considered:** Junction table `event_collective_bill_orders` — more normalized but duplicates snapshot/idempotency complexity already modeled by submitted-order rows. Defer unless denormalized columns prove insufficient.

### 2. List path: query membership in SQL, then reuse existing Python shaping

```
headers = EventCollectiveBill WHERE event_id = ?
orders = EdgeSubmittedOrder WHERE event_id = ? AND collective_bill_uuid IS NOT NULL
          (optional: OR uuid IN header uuids — same predicate)
group by collective_bill_uuid → existing _deduped_orders_for_bill / line_groups / DTO
```

Do not change dedupe or pricing helpers beyond feeding them a pre-filtered list.

### 3. Single bill: dedicated loader

`build_single_collective_bill(db, event, bill_uuid)` loads header (if any) + `WHERE event_id AND collective_bill_uuid = :uuid`, then runs the same shaping for one bill. PDF route keeps calling this helper.

### 4. Close detection: scoped query

`_maybe_close_collective_bill` uses `WHERE event_id AND collective_bill_uuid = header.uuid` (and payment checks on that set).

### 5. Ingest + backfill

- On edge order insert (and any update path that replaces payload), set denormalized fields from payload.
- Alembic migration: add columns + index; backfill with SQL `UPDATE ... SET collective_bill_uuid = payload->>'collective_bill_uuid'` (Postgres) and an ORM/SQLite-compatible backfill path used by tests/`apply_schema_patches` if that is the project’s dual-evolution pattern — follow whatever `010_edge_submitted_order_reporting_indexes` did for consistency.
- Treat empty string UUID as NULL.

### 6. Tests first

- Large fixture: many non-collective orders + few collective → list returns correct bills; assert query count or that a spy/helper is not given the full set (practical approach: unit-test the query helper returns only membership rows; integration test correctness).
- Close detection with unrelated open orders.
- Single-bill PDF path does not require other bills’ orders.
- Backfill: insert payload-only row, run backfill, list finds it.
- Existing `test_collective_bills.py` / PDF tests remain green.

## Risks / Trade-offs

- [Payload and column drift] → Single write path at ingest; backfill; optional assert in debug/tests that column matches payload when both set.
- [Snapshot rows / chunk entity_types] → Only denormalize for real order payloads; ignore non-order edge rows (entity_type chunks) the same way list filtering ignores missing UUID today.
- [SQLite vs Postgres JSON backfill] → Provide portable backfill in Python for tests; raw SQL for Postgres migration.
- [Partial indexes unsupported on SQLite] → Use plain composite index in ORM; partial index only in Postgres migration if desired.

## Migration Plan

1. Deploy migration (columns + index + backfill).
2. Deploy app code that writes columns on ingest and reads via SQL filters.
3. Rollback: revert app to Python filter (columns unused but harmless); dropping columns optional.

## Open Questions

- Whether denormalizing `payment_status` is worth a column vs JSON path on the already-narrowed bill order set (default: **no extra column** unless close detection profiling needs it).
- Whether list responses should eventually paginate bills — out of scope; note as future if bill counts grow large.
