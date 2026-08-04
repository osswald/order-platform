## 1. Schema and backfill

- [x] 1.1 Add Alembic migration for `EdgeSubmittedOrder.collective_bill_uuid` (nullable string) + composite index `(event_id, collective_bill_uuid)`
- [x] 1.2 Mirror the column/`index=True` (or explicit Index) on the SQLAlchemy model
- [x] 1.3 Implement Postgres SQL backfill from `payload->>'collective_bill_uuid'` and a portable ORM/SQLite backfill for tests
- [x] 1.4 Write failing tests: backfilled rows are found by SQL membership filter; empty-string UUID treated as NULL

## 2. Ingest alignment

- [x] 2.1 On edge submitted-order create (real order payloads), set `collective_bill_uuid` from payload
- [x] 2.2 Ensure non-order/chunk entity payloads do not incorrectly set membership
- [x] 2.3 Add/adjust edge ingest tests covering collective and non-collective orders

## 3. Query helpers and list path

- [x] 3.1 Add a helper that loads event collective orders via SQL (`event_id` + `collective_bill_uuid IS NOT NULL`), not `.all()` on the event
- [x] 3.2 Rewrite `build_event_collective_bills_list` to use the helper + existing dedupe/line-group shaping
- [x] 3.3 Add a large mixed-order fixture test asserting correct bills and that non-collective orders are not required in the loaded set
- [x] 3.4 Confirm existing `test_collective_bills.py` scenarios stay green

## 4. Close detection and single-bill path

- [x] 4.1 Rewrite `_maybe_close_collective_bill` to query only that bill’s orders; test close with unrelated open orders on the same event
- [x] 4.2 Rewrite `build_single_collective_bill` to load one bill’s header + orders without building the full multi-bill list
- [x] 4.3 Keep PDF route behavior; extend PDF/route tests if needed for single-bill scoping

## 5. Verification

- [x] 5.1 Run cloud backend pytest (`uv run pytest`) with collective-bill and reporting suites green
- [x] 5.2 Regenerate OpenAPI only if response schemas change (expected: no)
- [x] 5.3 Run `./scripts/lint.sh --staged` before commit
