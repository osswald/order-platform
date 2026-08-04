## Context

See `proposal.md` for motivation. Reporting today:

- `build_event_stats` loads all `EdgeOrderItem` for the event, filters `ordered_at` in Python (`event_stats.py`).
- `build_event_sales_report` loads all `EdgeSubmittedOrder` and aggregates from payloads (`event_sales.py`).
- `build_organisation_dashboard_summary` calls `build_event_sales_report` per prod event (`dashboard_summary.py`).
- Report routes often use `get_event_for_configuration` (heavy `selectinload` graph) via helpers.
- `EdgeOrderItem` already has composite indexes including `(event_id, ordered_at)` (migration lineage ~006); `EdgeSubmittedOrder.event_id` is weakly indexed.
- `edge_reporting.py` / sales-report-v3 already demonstrate SQL-oriented reporting — prefer converging rather than a third parallel aggregator.

`event-stats-timestamp-parsing` defines parse semantics for `ordered_at`; SQL filters must use timezone-aware UTC bounds consistent with that contract.

## Goals / Non-Goals

**Goals:**
- SQL-side time filters and aggregates for stats, dashboard summaries, and primary sales totals
- Slim event fetch for report routes
- Indexes for submitted-order (and related) hot FKs
- Keep admin UI JSON contracts stable enough that frontend changes are unnecessary or additive-only

**Non-Goals:**
- Edge bundle ETag CPU short-circuit
- Moving PDF generation to a background worker
- Full async SQLAlchemy rewrite
- Frontend bundle work (`cloud-admin-ui-perf`)
- Perfect bit-identical parity with every payload-JSON edge case if mirrors are the documented source of truth — capture intentional differences in tests

## Decisions

### 1. Canonical fact table: `EdgeOrderItem` (+ payment/batch mirrors as needed)

Use normalized mirrors for aggregates. Payload-based `EdgeSubmittedOrder` scans remain only where mirrors lack a fact the UI still needs (document each exception). Prefer extending v3/`edge_reporting` helpers over growing `event_sales` Python loops.

**Alternatives considered:** Materialized summary tables refreshed on sync — higher ops complexity; defer until SQL aggregates are insufficient. Redis cache of reports — hides the scan cost; fix the query shape first.

### 2. Dashboard: dedicated summary query, not N× full sales reports

Compute per-event or org-level revenue/order counts with grouped SQL filtered to the dashboard’s event set/statuses. Return the existing dashboard DTO fields.

**Alternatives considered:** Cache full sales reports in memory per request — still O(events × orders).

### 3. Stats: `WHERE event_id = ? AND ordered_at BETWEEN ? AND ?` then GROUP BY

Push category/source/article breakdowns into SQL where columns exist on `EdgeOrderItem`; keep thin Python only for shaping DTO keys the frontend expects.

**Alternatives considered:** Raw SQL views — optional later; start with SQLAlchemy `func.sum` / `group_by` for testability.

### 4. Lightweight `get_event_for_reporting` (name flexible)

New helper: tenancy + event row (+ org if needed) without stations/layouts/cells. Switch stats/sales/bookkeeping/transactions entrypoints to it. Leave configuration routes on `get_event_for_configuration`.

### 5. Transactions: default path stays SQL-paginated; eliminate all-rows “prior snapshot” when possible

Redesign prior-page diff/snapshot using keyset/`id < cursor` or a single window query. Retain in-memory fallback only for filters that cannot be expressed in SQL, gated and tested.

### 6. Indexes via Alembic (+ model `index=True` for clarity)

Add indexes for `EdgeSubmittedOrder.event_id`, `organisation_id` if missing; verify other FKs touched by new queries. Follow existing migration practices; avoid relying solely on `apply_schema_patches` for new indexes.

## Risks / Trade-offs

- [Aggregate mismatch vs old payload parser] → Golden tests comparing old vs new on fixture events before deleting Python path; document source of truth as mirrors.
- [NULL / naive `ordered_at` rows] → Reuse effective timestamp rules; ensure backfill assumptions from `event-stats-timestamp-parsing` / DB patches still hold; exclude or coalesce NULL consistently with today.
- [Collective bills / voucher lines special cases] → Phase: core stats+dashboard+sales totals first; bills/bookkeeping in follow-up tasks within the same change if time-boxed, else explicitly task-split.
- [Migration on large tables] → Use concurrent index creation if production requires it; for typical tenant sizes standard CREATE INDEX in migration is enough — call out in ops notes if concurrent needed.

## Migration Plan

1. Ship indexes migration first or in same deploy as query changes (indexes before heavy aggregates preferred).
2. Deploy backend; frontend unchanged if DTOs hold.
3. Rollback: revert app code; indexes may remain (safe).
4. Verify with pytest large fixtures + spot-check one real busy event in staging if available.

## Open Questions

- Exact dashboard field list that currently depends on full sales report (stock-outs, top articles, etc.) — inventory during implement and map each to SQL or accept a narrower summary.
- Whether sales-report-v3 can fully replace the legacy sales report UI path in this change or only power dashboard/stats first.
