## Context

See proposal.md — Why. After PRs 328/331, `pickup_prefix_mode` is stored on the event and included in Stammdaten Save, but the select was rendered on Stationen/Kassen and wired into configuration autosave via a second `PUT /events/{id}` with only `{ pickup_prefix_mode }`. That split is what made “Station” fail to stick.

## Goals / Non-Goals

**Goals:**

- Single ownership: mode UI + persist on Stammdaten.
- Remove the autosave↔event PUT bridge and related baseline helpers used only for that bridge.
- Stationen/Kassen keep mode-dependent letter fields; they receive mode as a prop, not an editable control.

**Non-Goals:**

- Changing allocation semantics, validation rules, mode lock after `config`, event copy, or Pi counters.
- Autosaving Stammdaten (mode stays on manual Speichern like other event fields).
- Backend schema or OpenAPI changes (unless tests reveal a real API gap).

## Decisions

### 1. Mode control lives in `EventStammdatenFields`

Place **Abholcode-Buchstabe von** in the existing **Konfiguration** field group (near cash-registers / feature toggles). Disable when `form.status !== 'config'` and show the existing locked hint.

**Alternatives considered:** Keep on Stationen with a dedicated “save mode now” button — still split ownership. Put under Zahlung — wrong mental model (not payment).

### 2. Persist only via existing Stammdaten Save

`Events.vue` `saveEvent` already sends `pickup_prefix_mode`. After the move, that is the only write path for mode in the admin UI.

**Remove / stop using for this purpose:**

- `pickupPrefixMode` in `eventConfigurationAutosaveSnapshot` / config watch
- `persistConfiguration`’s second event PUT
- `pickupPrefixModeSaved` emit + `stammdatenBaselineAfterPickupPrefixModeSave` wiring (helper may remain unused or be deleted if nothing else needs it)
- `v-model:pickup-prefix-mode` into `EventConfiguration` for *editing* — parent still passes mode down so letter fields show/hide

**Alternatives considered:** Keep dual-write “for convenience” — rejected; that is the bug source.

### 3. Stationen / Kassen: letter fields only

- Remove mode `v-select` blocks from `EventConfigStationsSection` and `EventConfigCashRegistersSection`.
- Keep `:pickup-prefix-mode` prop (and lock is irrelevant for a removed control; lock stays on Stammdaten).
- Prefix letter visibility unchanged (`register` → register prefixes; `station` → station prefixes).

### 4. Tests first

- Frontend: Stammdaten fields render mode select; locked when not `config`; Stationen/Kassen no longer expose mode select; saving Stammdaten payload includes `pickup_prefix_mode: 'station'`.
- Backend (if missing): HTTP PUT event with `pickup_prefix_mode: station` then GET returns `station`.
- Drop or rewrite tests that asserted mode control on Stationen/Kassen sections.

## Risks / Trade-offs

- **[Risk] Operators expect autosave for mode** → Mitigation: mode is next to other Speichern-only toggles; status bar already reflects Stammdaten dirty.
- **[Risk] Changing mode without saving Stammdaten, then editing stations** → Letter fields follow in-memory mode immediately; DB mode updates only on Speichern. Acceptable and consistent with other Stammdaten flags that gate config UI.
- **[Risk] Incomplete cleanup leaves dead second PUT** → Tasks explicitly remove bridge code and update tests so CI fails if the control returns on Stationen.

## Migration Plan

1. Ship cloud frontend-only change (no DB migration).
2. No Pi deploy required.
3. Rollback: revert frontend PR; backend unchanged.

## Open Questions

None.
