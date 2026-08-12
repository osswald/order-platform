## Why

Rentals are the only valid home for appliance lendings, but several cloud admin surfaces still behave as if lendings were free-floating: rental edit cannot add devices, appliance and organisation “lend” flows always spawn a new rental, and lists omit rental context. Operators also need same-day handover (return day free, and open end date D may start a new rental on D).

## What Changes

- **Rental edit (Ausleihe)**: add appliances to an existing rental; keep unassign (planned) / return (current). Create rental stays empty (no device picker).
- **Appliance detail lend**: require choosing an existing rental for the organisation **or** creating a new rental, then assign; success is toast-only (stay on page).
- **Appliance lending history/detail**: group lendings under foldable rental headers, newest rental first; expose rental identity on lending reads.
- **Organisation Geräte tab (Option X)**: keep a device-centric list but show rental display name (and link toward Ausleihe where practical); include **past** alongside current/planned; lend dialog uses the same pick-existing-or-create-new rental flow, then multi-select devices.
- **Overlap / availability**: an appliance returned on day D may be lent again on D; an open lending that **ends** on D does **not** block a new open lending that **starts** on D (handover day). Real multi-day overlap still rejected.
- On a shared handover day, “active today” / edge status prefers the lending that **starts** that day when more than one open lending covers D.

## Capabilities

### New Capabilities

- `rental-lending-entry-points`: Appliance detail and organisation Geräte lending UX must be rental-aware (pick or create rental, rental-grouped history, rental column + past on org tab).

### Modified Capabilities

- `rental-containers`: Handover-day and return-day availability; lending reads expose rental identity; assign/unassign membership remains the only way to “edit” lendings (no per-device dates).
- `rental-calendar`: Rental edit dialog can add appliances; create remains empty of devices.

## Impact

- **Cloud backend**: overlap helper (`find_open_overlap` / lend_check) and any “active today” resolution; lending DTOs on appliance/org reads include `rental_id` + display name; OpenAPI + generated frontend types.
- **Cloud frontend**: `RentalsCalendar.vue` edit add-device; `Appliances.vue` lend + grouped history; `Organisations.vue` / `OrganisationLendingDialog.vue` (and possibly `ApplianceLendings.vue` consistency); i18n de/en; Vitest.
- **Edge / Pi**: only if “current lending for today” resolution changes when two open lendings touch on D — prefer the one that starts on D.
- **Out of scope**: per-lending independent date ranges; changing rental organisation after create; fleet busy-cell click-to-edit; rental↔event linking.
