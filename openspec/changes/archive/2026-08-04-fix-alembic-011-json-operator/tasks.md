## 1. Tests first

- [x] 1.1 Add a guard test that revision `011` Postgres backfill SQL does not use jsonb-only `?` on `payload` (and preferably asserts `->>` / equivalent json-safe predicate)
- [x] 1.2 Run the new test and confirm it fails against the current broken migration

## 2. Fix migration

- [x] 2.1 Update `011_edge_submitted_order_collective_bill_uuid.py` Postgres branch to use json-safe key/value checks (`payload->>'collective_bill_uuid' IS NOT NULL` or equivalent)
- [x] 2.2 Re-run the guard test and related alembic/schema tests; confirm pass

## 3. Verify

- [x] 3.1 Run cloud backend test suite (or at least migration + collective-bill reporting tests)
- [x] 3.2 Run `./scripts/lint.sh --staged` (or full lint) before commit readiness
- [x] 3.3 Mark OpenSpec tasks complete; note VPS apply/restart remains a separate operator step after merge/deploy
