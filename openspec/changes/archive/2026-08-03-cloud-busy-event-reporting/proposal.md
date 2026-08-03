## Why

Busy-event admin surfaces (organisation dashboard, event stats, sales report, bookkeeping, collective-bill scans) load entire `EdgeSubmittedOrder` / `EdgeOrderItem` sets into Python and aggregate in memory — and the dashboard repeats a full sales report per production event. That pattern already stresses large events and will not scale; normalized `EdgeOrderItem` tables and their `ordered_at` indexes exist but are underused for these paths.

## What Changes

- Push time-range filtering and core aggregations for event stats, sales summaries, and organisation dashboard totals into SQL over `EdgeOrderItem` (and related mirror tables), instead of `.all()` + Python loops.
- Stop calling `build_event_sales_report` once per prod event on the dashboard; compute org/event summary metrics with set-oriented queries.
- Slim report route event loads: reporting handlers that only need event identity/org must not pay the full configuration eager-load graph.
- Fix transaction pagination paths that still load all orders for “prior snapshot” / kind filtering when a windowed or SQL-side approach can preserve behavior.
- Add missing indexes on hot reporting FKs if not already present (`EdgeSubmittedOrder.event_id` / organisation, and any other columns proven hot by these queries).
- Preserve existing JSON response shapes for admin UI consumers where practical; document any additive fields. No intentional **BREAKING** response removals.
- Prefer the normalized reporting path (`edge_reporting` / v3-style) as the canonical aggregate source where it already matches UI needs; avoid duplicating divergent Python aggregators.

## Capabilities

### New Capabilities
- `cloud-busy-event-reporting`: Performance and correctness requirements for cloud admin event/organisation reporting (stats, sales summary, dashboard, bookkeeping inputs) using SQL-side aggregation over edge order mirrors, without changing operator-facing report meaning.

### Modified Capabilities
- (none — `event-stats-timestamp-parsing` remains the ordered_at parse contract; this change uses those timestamps in SQL filters rather than altering parse rules)

## Impact

- **Cloud backend**: `event_stats.py`, `event_sales.py`, `dashboard_summary.py`, `event_bookkeeping.py`, `event_transactions.py`, `event_collective_bills.py` (as needed), `routers/events_reports.py`, `routers/organisations.py`, models/migrations for indexes, possibly `edge_reporting.py`.
- **Cloud frontend**: Ideally no UI changes if response shapes hold; update tests/fixtures if field nesting shifts additively.
- **OpenAPI**: Regenerate only if response schemas change.
- **Tests**: Expand backend pytest coverage for stats/sales/dashboard with multi-thousand-item fixtures asserting shape parity and that queries do not load unbounded row sets into Python for aggregates.
- **Out of scope**: Edge bundle ETag CPU short-circuit, frontend Chart.js lazy load (covered by `cloud-admin-ui-perf`), PDF generation offload to a worker queue, full async SQLAlchemy migration.
