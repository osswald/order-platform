## Why

Collective-bill (Sammelrechnung) list, close detection, and single-bill PDF still load every `EdgeSubmittedOrder` for an event and filter `payload.collective_bill_uuid` in Python. That was the residual gap after `cloud-busy-event-reporting`; busy events with many non-collective orders still pay a full order-table scan whenever an operator opens bills or a bill closes on sync.

## What Changes

- Make collective-bill order membership queryable in SQL (denormalized columns and/or expression indexes), not via full-event payload scans.
- Rewrite `build_event_collective_bills_list`, `_maybe_close_collective_bill`, and `build_single_collective_bill` to load only orders that belong to collective bills (and, for single-bill PDF, only that bill’s orders).
- Populate the queryable fields on edge order ingest / upsert; backfill existing rows.
- Preserve admin list/PDF JSON shapes; no intentional **BREAKING** API changes.
- Keep payload JSON as the source for line/payment detail after the narrowed order set is loaded.

## Capabilities

### New Capabilities
- `cloud-collective-bill-reporting-perf`: Performance requirements for cloud admin collective-bill listing, close detection, and single-bill PDF/detail loading without full-event submitted-order scans.

### Modified Capabilities
- (none — `cloud-busy-event-reporting` is an in-flight/complete change capability not yet archived into `openspec/specs/`; this follow-up is a separate capability)

## Impact

- **Cloud backend**: `event_collective_bills.py`, edge order ingest in `routers/edge.py`, `models.EdgeSubmittedOrder`, Alembic migration + backfill, `routers/events_reports.py` (behavior unchanged, faster path), tests (`test_collective_bills.py`, PDF/route tests, new perf-oriented fixtures).
- **Cloud frontend**: No UI changes if response shapes hold.
- **Pi / edge**: No protocol change; cloud denormalizes from existing payload fields (`collective_bill_uuid`, `payment_status`, …).
- **Out of scope**: Moving PDF generation off the request path; rewriting line aggregation onto `EdgeOrderItem` mirrors (optional later); frontend pagination of bill lists.
