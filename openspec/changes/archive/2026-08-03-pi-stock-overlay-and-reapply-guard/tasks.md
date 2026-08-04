## 1. Reapply guard (G)

- [x] 1.1 Add failing tests: `pull_and_restore` on 304 / identical-body with pending outbox does not double-decrement effective stock and does not rewrite `SyncedBundle.json_body` for reapply
- [x] 1.2 Add failing test: real `bundle_changed` pull still reapplies pending outbox onto the new baseline
- [x] 1.3 Gate `reapply_pending_stock` in `pull_and_restore` on `bundle_changed`; skip durable stock persist when reapply is a no-op; keep explicit reapply after restore that replaces baseline

## 2. Local stock overlay (F)

- [x] 2.1 Add failing tests: order stock path updates effective sellable without changing catalogue `json_body` / `updated_at`; cold load after “restart” (invalidate + new session) still merges overrides
- [x] 2.2 Add Alembic revision after `008_hot_path_indexes` for overlay table + unique `(event_id, entity_kind, entity_id)`; align ORM / `init_test_schema` patches as needed
- [x] 2.3 Implement merge-on-read in bundle helpers (catalogue ⊕ overlay → effective cache) and stock persist that upserts overlay + updates cache without rewriting catalogue JSON
- [x] 2.4 On catalogue persist (real pull / restore baseline replace): clear overlay, reapply pending when required, upsert overlay from result (or leave empty when no pending stock)
- [x] 2.5 Route order-create, reapply, and restore stock call sites through the new persist helpers; keep `ensure_instant_collective_bills_for_bundle` on catalogue writes only

## 3. Verification

- [x] 3.1 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [x] 3.2 Run `./scripts/lint.sh --staged` (or full) before commit
