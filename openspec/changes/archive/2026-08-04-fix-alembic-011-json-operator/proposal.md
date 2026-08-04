## Why

Production `cloud-backend` crash-loops after deploy because Alembic revision `011_edge_submitted_order_collective_bill_uuid` uses the PostgreSQL `?` containment operator on `edge_submitted_orders.payload`, which is typed `json` (not `jsonb`). The operator does not exist for `json`, so every startup `upgrade head` fails, workers exit, and `api.vendiqo.ch` returns 502.

## What Changes

- Fix migration `011` backfill SQL to use JSON operators valid for Postgres `json` (e.g. `payload->>'collective_bill_uuid' IS NOT NULL` instead of `payload ? 'collective_bill_uuid'`).
- Add/adjust tests so this Postgres `json` vs `jsonb` footgun is caught before deploy.
- No schema/API behaviour change beyond making the already-intended backfill runnable on production.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `cloud-collective-bill-reporting-perf`: Clarify that the collective-bill UUID backfill MUST use SQL compatible with Postgres `json` columns (not jsonb-only operators), so production upgrades succeed.

## Impact

- `cloud/backend/alembic/versions/011_edge_submitted_order_collective_bill_uuid.py`
- Cloud backend migration tests
- Production VPS recovery: after merge/deploy (or one-shot apply of the fixed revision), `alembic_version` can advance from `009` through `010`/`011` and `cloud-backend` can stay up
