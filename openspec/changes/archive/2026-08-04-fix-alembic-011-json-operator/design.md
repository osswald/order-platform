## Context

Cloud production `edge_submitted_orders.payload` is SQLAlchemy/`JSON` → Postgres type `json`. Revision `011_edge_submitted_order_collective_bill_uuid` backfills `collective_bill_uuid` with a Postgres `?` key-existence check that only works on `jsonb`. After deploy of PR #253-era migrations, every gunicorn worker runs `upgrade head` on startup, hits that SQL, rolls back, and exits — leaving `alembic_version` at `009_cash_session_uuid` and `api.vendiqo.ch` returning 502.

SQLite (most CI tests) does not exercise the Postgres branch, so the bug shipped.

## Goals / Non-Goals

**Goals:**
- Make revision `011` runnable on production Postgres with `json` payload columns.
- Preserve backfill semantics: rows with a non-empty `payload.collective_bill_uuid` get the denormalized column; others stay NULL.
- Cover the Postgres SQL with a test that fails on jsonb-only operators.
- Unblock VPS recovery after the fixed revision is deployed (or applied once).

**Non-Goals:**
- Converting `payload` from `json` to `jsonb` (larger migration; not required for this outage).
- Changing gunicorn worker count or moving migrations out of lifespan (worthwhile later; not needed to restore service once `011` is fixed).
- Changing collective-bill query APIs or admin UI contracts.

## Decisions

1. **Replace `payload ? 'collective_bill_uuid'` with `(payload->>'collective_bill_uuid') IS NOT NULL`**
   - Rationale: `->>` is valid for both `json` and `jsonb` on Postgres; empty/whitespace values are already normalized by `NULLIF(TRIM(...), '')` in the SET clause.
   - Alternatives: `payload::jsonb ? 'key'` (works but casts every row; unnecessary); switch column to jsonb (out of scope).

2. **Edit the existing `011` revision in place (not a new `012`)**
   - Rationale: Production never successfully applied `011` (`alembic_version` still `009`). Editing the failed revision is safe and avoids a no-op stuck revision.
   - Constraint: If any environment already stamped `011`, it would not re-run — not the case for prod; local/dev that partially applied should re-check.

3. **Test via asserting the migration source / executing the Postgres upgrade path**
   - Prefer a focused unit/guard test that the upgrade SQL does not use jsonb-only `?` on `payload`, plus existing alembic upgrade-to-head coverage on SQLite for the non-Postgres branch.
   - Optional: if a Postgres CI path exists for migrations, exercise `011` there; do not block the hotfix on adding a new Postgres service if none is ready.

## Risks / Trade-offs

- **[Risk] Environments that already stamped broken `011` without backfill** → Unlikely for prod; if found, add a follow-up data backfill script or `012` repair revision.
- **[Risk] Dual gunicorn workers still race on first successful upgrade** → Alembic transactional DDL usually lets one win; after `011` is applied once, subsequent boots are no-ops. Acceptable for hotfix; advisory lock can be a follow-up.
- **[Trade-off] `->>` IS NOT NULL treats key-present-but-null JSON differently from `?`** → Matches intended backfill (`NULLIF(TRIM(...))`); empty strings already become NULL.

## Migration Plan

1. Land fixed `011` via PR on `main`.
2. On VPS: rebuild/restart `cloud-backend` (or one-shot `alembic upgrade head` with fixed image) so `010`+`011` apply once.
3. Verify `alembic_version` = `011_...`, `/health` 200, admin API usable.
4. Rollback: revert image to pre-`010`/`011` only if needed for code; DB can remain at `011` once applied (forward-compatible). Do not roll back `alembic_version` without downgrade.
