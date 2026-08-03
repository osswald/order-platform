## Context

Cash shift sessions (`CashSession` on Pi, `EdgeCashSession` on cloud) track float, wallet, and ledger for waiters and cash registers when `shift_settlement_enabled` is on. Pi already allows closing a shift and opening another for the same subject on the same event (409 only if one is already OPEN). Cloud upsert currently keys on `(organisation_id, event_id, subject_key)`, so sequential shifts for the same waiter/register collapse to one admin row.

Cross-appliance restore uses `subject_key` to find the OPEN session for a subject. That job must stay separate from durable history identity.

## Goals / Non-Goals

**Goals:**

- Stable per-shift identity (`cash_session_uuid`) minted at open for waiters and registers.
- Cloud stores and lists every synced shift for an event (multiple rows per subject).
- Preserve ≤1 OPEN shift per (event, subject).
- Keep open-session restore filtered by subject + OPEN status without deleting closed history.
- Forward-only rollout; existing admin Schichten list is the reporting surface.

**Non-Goals:**

- Backfilling shifts already overwritten in cloud.
- New export/PDF/settlement report surfaces.
- Changing Pi waiter UX for open/close beyond what already works.
- Concurrent open shifts for the same subject.

## Decisions

### 1. Identity field: `cash_session_uuid`

- **Choice:** UUID v4 (or equivalent) generated on Pi at `open_session`, persisted on `CashSession`, included in every sync payload.
- **Why not** reuse local integer `cash_session_id` alone: appliance-local; collisions across Pis break org-wide uniqueness.
- **Why not** `subject_key + started_at`: brittle under clock skew / re-sync; UUID is explicit.

Local `id` / `cash_session_id` remain for SQLite FKs and debugging; cloud may keep `cash_session_id` as informational.

### 2. Cloud unique key: `(organisation_id, event_id, cash_session_uuid)`

- **Choice:** Replace uniqueness on `subject_key` with uniqueness on `cash_session_uuid` (scoped by org + event).
- `subject_key` stays as a non-unique column for listing filters and restore selection of OPEN rows.
- Upsert matches on org + event + `cash_session_uuid`; re-sync of the same shift updates that row in place (OPEN → CLOSED, ledger growth).

**Alternative considered:** Archive-on-close + overwrite current — rejected as dual-write complexity.

### 3. Same rules for waiters and cash registers

- Subject types `waiter` and `cash_register` both mint UUID, both may have multiple historical rows, both still have at most one OPEN per event.

### 4. Restore / snapshot

- Operational snapshot continues to include **OPEN** cash sessions only.
- Restore still applies open sessions by subject (`waiter_uuid` / `cash_register_uuid` / `subject_key`).
- Prefer matching an existing local OPEN for that subject; if applying a cloud OPEN, carry `cash_session_uuid` when present so subsequent syncs do not create a duplicate cloud row.

### 5. Forward-only migration

- Drop or replace unique index `ix_edge_cash_sessions_org_event_subject` (or equivalent) after adding the new unique index on `cash_session_uuid`.
- Rows without `cash_session_uuid` (legacy): leave as-is; new opens always set UUID. Optional one-time: generate UUIDs for existing cloud rows that lack them so the new unique constraint can be NOT NULL — prefer nullable UUID + unique among non-null, or backfill random UUIDs for current rows only (not reconstructing lost history). Prefer **backfill UUID for existing rows** so the column can be NOT NULL going forward without inventing false history.

### 6. Admin API / UI

- `GET .../cash-sessions` already returns a paginated list; no API shape change required beyond exposing `cash_session_uuid` if useful for support.
- Schichten tab already expands ledger per row; verify two closed shifts for the same waiter both appear.

## Risks / Trade-offs

- **[Risk]** Mixed old/new Pis: old payload without UUID could fail upsert or collide → **Mitigation:** reject or no-op cash_session chunks missing UUID after deploy; document appliance upgrade expectation. During transition, if UUID missing, fall back to legacy subject_key upsert only for that chunk (documented deprecation) — prefer hard require UUID once Pi ships the field to avoid silent overwrite.
- **[Risk]** Two OPEN rows for same subject if bug or dual-appliance race → **Mitigation:** keep Pi 409 on open; restore/snapshot only advertise OPEN; optional cloud warning later (out of scope).
- **[Risk]** Index migration on production `edge_cash_sessions` → **Mitigation:** Alembic: add column, backfill UUIDs for existing rows, add unique index, drop old unique index.
- **[Trade-off]** Forward-only means some historical shifts remain lost — accepted.

## Migration Plan

1. Ship Pi generating and syncing `cash_session_uuid`.
2. Ship cloud accepting UUID, dual-read upsert (UUID preferred), then enforce unique on UUID and drop subject uniqueness.
3. Roll appliances so new shifts always carry UUID.
4. Rollback: re-adding subject unique would again collapse history — avoid unless emergency; prefer forward fix.

## Open Questions

- None blocking; field name locked as `cash_session_uuid` (aligned with `CashSession` entity).
