## Context

See proposal.md for motivation. Today Pi allocates `pickup_code = {cash_register.pickup_code_prefix}{n}` with a single `event_pickup_counters` row per event; station-scoped pickups already create one code per production-station group. Cloud event status lifecycle is `config` → `test` → `prod` → `archive`. Event configuration is synced to Pi via the edge bundle. Printer-rule `pickup_prefix` only routes prints and must stay separate from allocation prefixes.

## Goals / Non-Goals

**Goals:**

- Event-level `pickup_prefix_mode` (`register` | `station`) with matching allocation on Pi.
- Config UI shows only the prefixes for the active mode.
- Station mode: unique required station prefixes (1–3 `A–Z`), per-station counters, no null-station article lines.
- Mode immutable once status ≠ `config`.
- Event copy preserves mode and the prefixes that mode uses.

**Non-Goals:**

- Changing printer-rule `pickup_prefix` semantics or UI.
- Per-register counters, waiter/table pickup codes, or renumbering historical codes.
- Requiring mode lock on prefix *value* edits (only the mode enum is locked after `config`).

## Decisions

### 1. Field names and storage (cloud)

- `events.pickup_prefix_mode` — `String(16)`, not null, default `'register'`.
- `event_stations.pickup_code_prefix` — `String(3)`, **nullable**. Required (non-null, valid) only when mode is `station`.
- Keep `event_cash_registers.pickup_code_prefix` not null as today. In station mode the column remains stored (last value / default) but is unused for allocation and hidden in UI so flipping back to register in `config` does not lose data.

**Alternatives considered:** Make register prefix nullable in station mode — more schema churn for little gain. Separate “display prefix” table — overkill.

### 2. Mode lock

- Cloud rejects updates that change `pickup_prefix_mode` when `event.status` is not `config` (HTTP 422, stable error code e.g. `pickup_prefix_mode_locked`).
- UI disables the mode control outside `config`.
- Prefix *values* for the active mode remain editable in `test`/`prod` (existing ops flexibility); only the mode switch is frozen.

**Alternatives considered:** Lock when any pickup counter > 1 — races with bundle timing and is harder to explain. Lock all prefixes after `config` — stricter than requested.

### 3. Station-mode validation (cloud save)

When `pickup_prefix_mode == station`:

- Every station has `pickup_code_prefix` matching `^[A-Z]{1,3}$`.
- Prefixes are unique among stations on the event (case-normalized to upper).
- Existing rule remains: every app-layout article must be in the station article union (“all articles require a station”).
- Register prefix validity is not required for save (values may be stale); still keep DB non-null via defaults if registers are created.

When mode is `register`: station prefixes may be null/ignored; register prefixes stay required as today.

### 4. Bundle + Pi allocation

- Bundle includes `pickup_prefix_mode` on the event and `pickup_code_prefix` on each station.
- Allocation for cash-register orders:
  - **register:** prefix = register’s `pickup_code_prefix`; number = `_allocate_pickup_number(event_id)` (unchanged).
  - **station:** prefix = that group’s station `pickup_code_prefix`; number = `_allocate_pickup_number(event_id, station_uuid=…)`; if `station_uuid` is null → fail the order (config invariant broken).
- Multi-station orders still burn one number per group; numbers are independent sequences per station.

### 5. Pi counter schema

Extend `event_pickup_counters`:

| Column | Role |
|--------|------|
| `event_id` | event |
| `station_uuid` | `NULL` = register-mode (event-wide) row; non-null = station-mode row |
| `next_number` | next int to issue |

Unique constraint on `(event_id, station_uuid)` with a **single** NULL `station_uuid` row per event for register mode (SQLite: use partial unique index or sentinel `''` if NULL uniqueness is awkward — prefer empty-string sentinel `station_uuid = ''` for the event-wide row to keep one unique index).

**Alternatives considered:** Separate `event_station_pickup_counters` table — clearer but doubles restore/purge paths. Composite only without register-mode row — would force inventing a fake station uuid.

### 6. Operational restore / purge / test→prod reset

- Restore max pickup: in register mode, parse all codes’ numeric suffixes for the event (as today). In station mode, parse per `station_uuid` (from `station_pickups` / payloads) and bump each station counter.
- Event lifecycle purge continues to delete **all** counter rows for the event (event-wide sentinel and every per-station row).
- **test → prod** already calls that purge on Pi (`reconcile_bundle_lifecycle` → `purge_event_local_data`). Preserve that path for the new counter shape so the first production allocation restarts at `1` for each series. No separate “reset counters only” API — purge remains the mechanism.

### 7. Event copy

- Copy `pickup_prefix_mode`.
- Copy each station’s `pickup_code_prefix`.
- Register prefixes already copied; keep doing so even in station mode (hidden values travel with the clone).

### 8. Config UI

- Event configuration: mode select/toggle near stations/registers (label e.g. “Abholcode-Buchstabe von”).
- `register` → show register prefix inputs; hide station prefix inputs.
- `station` → opposite.
- Mode control disabled when status ≠ `config`, with short explanation.

### 9. OpenAPI / types

- Export OpenAPI after schema changes; regenerate cloud frontend API types in the same PR.

## Risks / Trade-offs

- **[Risk] Mid-event station prefix edits still allowed** → Codes issued before/after an edit can share a letter with different meaning. Accept for v1; document; revisit if ops complain.
- **[Risk] SQLite unique NULL for counters** → Mitigate with `station_uuid = ''` sentinel for event-wide row.
- **[Risk] Stale register prefixes in station mode** → Harmless for allocation; if user flips back in `config`, old letters return — intended.
- **[Risk] Bundle/Pi version skew** → Old Pi ignores unknown fields and keeps register behaviour; new cloud + old Pi with station mode would mis-allocate. Mitigate: document that station mode requires Pi build that understands the mode (same release train as today for config features).

## Migration Plan

1. Cloud: add columns with defaults (`pickup_prefix_mode='register'`, station prefix null); no backfill required.
2. Pi: Alembic migration for counter shape + read new bundle fields; register mode path identical to today.
3. Deploy cloud then Pi (or together); default mode keeps behaviour unchanged.
4. Rollback: ignore new fields / leave mode at `register`; station prefixes unused.

## Open Questions

None — product decisions from explore are locked (event switch, per-station counters, articles on stations, mode flip forbidden after `config`, copy mode+prefixes, 1–3 letter prefixes, test→prod resets counters).
