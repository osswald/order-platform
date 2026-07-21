## Why

Cloud event detail mixes manual stammdaten save with debounced configuration/stock/receipt autosave. Confirming a status transition (config → test → prod → archive) only updates local form state, so operators can believe the change stuck when it did not. Successful create/edit saves also navigate back to the event list. Autosave can stall when temporarily disabled (layout cell load/dialog), leaving dirty state without a restart — so saves feel unreliable.

## What Changes

- After the operator confirms a status transition in the event status stepper, persist **only** `status` via `PUT /events/{id}` (no other stammdaten fields). Stay on the event detail; update local baseline/`originalStatus` on success; revert UI and show an error on failure.
- After a successful **create** or **edit** of event stammdaten, **remain on the event detail** (create navigates to the new event’s detail; edit does not return to the list).
- Harden shared dirty autosave so that when `enabled` becomes true again while dirty, a save is rescheduled (and pending debounce is not silently dropped solely because autosave was paused). Prefer flushing pending saves on leave where practical so navigations do not discard queued work without user awareness beyond `beforeunload`.
- Stammdaten fields other than status remain on the existing manual Save button for this change (status is an immediate action; config/stock/receipts keep autosave).

## Capabilities

### New Capabilities

- `cloud-event-save`: Operator-facing event detail save behavior — status-only persistence on confirmed transition, stay-on-detail after create/edit save, and stable debounced autosave for configuration (and shared autosave composable) silos.

### Modified Capabilities

- (none — `event-configuration-perf` covers backend load/PUT duration; this change does not alter those requirements)

## Impact

- **Cloud frontend:** `Events.vue`, `EventStatusStepper.vue`, `useDirtyAutosave` (and tests), possibly `EventConfiguration.vue` / `EventSaveStatusBar.vue` for status-save feedback and dirty accounting when status is no longer only a local stammdaten field.
- **Cloud backend:** No schema/API change expected — `EventUpdate` already supports partial updates including status-only PUT with existing transition validation and test→prod purge.
- **Help/i18n:** Minor copy if status-confirm or save messaging needs to reflect immediate persistence; update help only if it currently implies Save is required for status.
- **Out of scope:** Stammdaten field autosave; backend config payload splitting; Pi event UI.
