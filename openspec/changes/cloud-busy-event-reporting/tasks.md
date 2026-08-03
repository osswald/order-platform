## 1. Baseline, indexes, and fixtures

- [ ] 1.1 Inventory dashboard summary fields that currently depend on `build_event_sales_report` and map each to SQL/`EdgeOrderItem` (or document an exception)
- [ ] 1.2 Add Alembic migration + model indexes for `EdgeSubmittedOrder.event_id` and organisation scope columns used by reporting if missing
- [ ] 1.3 Write failing pytest fixtures with large order-item volumes asserting stats time-window behavior and dashboard summary shape
- [ ] 1.4 Add golden/parity tests comparing key totals from the legacy path vs the intended SQL path on small fixtures before switching callers

## 2. Lightweight event load for reports

- [ ] 2.1 Add a reporting-oriented event loader (tenancy + event/org only; no stations/layouts/cells graph)
- [ ] 2.2 Switch stats, sales, bookkeeping, transactions, and related report routes to the lightweight loader
- [ ] 2.3 Keep configuration routes on the existing configuration loader; add tests that report handlers do not require layout cells

## 3. Event statistics SQL path

- [ ] 3.1 Filter `EdgeOrderItem` by `event_id` + `ordered_at` range in SQL (UTC-aware bounds consistent with ordered_at parsing rules)
- [ ] 3.2 Move core stats aggregates/group-bys into SQLAlchemy/`func` queries; keep DTO shaping thin in Python
- [ ] 3.3 Ensure empty-window and no-orders cases match current empty payload behavior
- [ ] 3.4 Make large-volume stats tests pass without loading the full event item set into Python for filtering

## 4. Dashboard and sales aggregates

- [ ] 4.1 Replace per-prod-event `build_event_sales_report` calls in dashboard summary with set-oriented summary queries
- [ ] 4.2 Implement SQL-based sales headline totals / primary breakdowns (prefer extending `edge_reporting` / v3 helpers over growing payload scanners)
- [ ] 4.3 Preserve admin UI JSON fields used today; regenerate OpenAPI only if schemas change
- [ ] 4.4 Decide and document: v3/mirrors as source of truth where legacy payload aggregates disagree; encode in tests

## 5. Transactions pagination cleanup

- [ ] 5.1 Remove default-path full-table loads used only for prior-snapshot/diff when building a created-at page
- [ ] 5.2 Implement windowed/keyset or equivalent prior-page logic compatible with existing pagination metadata
- [ ] 5.3 Gate any remaining in-memory fallback to documented non-default filters; cover both paths in tests

## 6. Follow-on report surfaces (same change if feasible)

- [ ] 6.1 Apply SQL filtering/aggregation to bookkeeping inputs where they share the load-all pattern
- [ ] 6.2 Reduce collective-bill full order scans where JSON facts can be queried or narrowed; otherwise note residual limitation in design/PR
- [ ] 6.3 Remove or shrink dead Python aggregation paths that are no longer called

## 7. Verification

- [ ] 7.1 Run cloud backend pytest suite (`uv run pytest`) with new reporting/index tests green
- [ ] 7.2 Spot-check OpenAPI/frontend only if response shapes changed
- [ ] 7.3 Run `./scripts/lint.sh --staged` (or backend ruff via lint script) before commit
