## Why

Hire-company admins can create rentals from the Ausleihe calendar, but clicking an existing rental bar still falls through to “create for this day.” Operators need to open a rental, change its label/dates, manage assigned devices, and delete/cancel when allowed — without leaving the calendar.

## What Changes

- Clicking a rental bar on the **month** or **year** view opens an edit dialog for that rental (not create).
- Edit supports: optional label, start/end dates, read-only organisation, list of assigned lendings with unassign (planned) / return (current), and delete/cancel when the existing rental delete rules allow it.
- Empty day/track clicks keep creating a new rental. Fleet view behaviour is unchanged (no click-to-edit on busy cells in this change).
- Organisation remains immutable after create (no PATCH of `organisation_id`).
- No new backend endpoints required if existing `GET`/`PATCH`/`DELETE` `/rentals/{id}` and assign/unassign already cover the flows; UI wires them and surfaces overlap/delete errors clearly.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `rental-calendar`: Clicking month/year rental bars opens edit; create remains on empty day/track; edit dialog includes label, dates, device list actions, and delete when allowed.
- `rental-containers`: Clarify that organisation is immutable after create; edit path uses existing PATCH/DELETE/assign/unassign rules (delta only where calendar edit exposes behaviour that was API-only).

## Impact

- **Cloud frontend**: `RentalsCalendar.vue` (chip/bar click handling, edit dialog), i18n (de/en), help article update, Vitest coverage for open-edit vs create and delete visibility.
- **Cloud backend**: likely no schema change; may need small read/error polish only if delete/overlap messages are weak for UI. OpenAPI regenerate only if schemas change.
- **Edge / Pi**: none.
- **Out of scope**: changing organisation; fleet busy-cell edit; drag-resize bars; rental↔event linking.
