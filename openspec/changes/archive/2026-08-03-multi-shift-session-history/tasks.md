## 1. Tests first (Pi)

- [x] 1.1 Add Pi test: open → close → open same waiter yields two rows with distinct `cash_session_uuid`; second open while OPEN returns 409
- [x] 1.2 Add Pi test: register subject gets `cash_session_uuid` in open + sync payload
- [x] 1.3 Add Pi restore test: applying cloud OPEN carries/preserves `cash_session_uuid` when present

## 2. Pi implementation

- [x] 2.1 Add `cash_session_uuid` column to Pi `CashSession` (model + schema patch/migration as used locally)
- [x] 2.2 Mint UUID in `open_session`; include in `session_to_sync_payload` and shift API responses
- [x] 2.3 Update operational restore to set `cash_session_uuid` from cloud payload when restoring OPEN sessions
- [x] 2.4 Run Pi cash-session / shift / restore tests

## 3. Tests first (Cloud)

- [x] 3.1 Add cloud test: two sequential closed waiter sessions with different UUIDs both persist and appear in `build_cash_sessions_page`
- [x] 3.2 Add cloud test: re-sync same `cash_session_uuid` updates one row (OPEN → CLOSED)
- [x] 3.3 Add cloud test: operational snapshot includes only OPEN session when CLOSED + OPEN share a subject

## 4. Cloud implementation

- [x] 4.1 Alembic: add `cash_session_uuid`, backfill UUIDs for existing rows, unique on `(organisation_id, event_id, cash_session_uuid)`, drop unique on `subject_key`
- [x] 4.2 Change `upsert_edge_cash_session` to match on `cash_session_uuid`; require UUID on ingest for new writes
- [x] 4.3 Expose `cash_session_uuid` on cash-session read schema / list items; regenerate OpenAPI + frontend types if schemas change
- [x] 4.4 Confirm snapshot builder still filters `status == OPEN` and does not delete closed rows on newer subject sync
- [x] 4.5 Run cloud edge cash-session / snapshot / related tests

## 5. Admin UI smoke + docs

- [x] 5.1 Verify Schichten tab shows multiple rows per waiter/register (manual or existing list wiring); no UX redesign
- [x] 5.2 Update help copy only if it currently implies one shift per waiter/register (optional, skip if already neutral)
- [x] 5.3 Run `./scripts/lint.sh` on touched areas; ensure all related tests pass
