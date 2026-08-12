## Why

Hire-company operators already think in **rentals** (a dated commitment to an organisation), but the product only stores ungrouped per-appliance lendings. There is no way to hold a weekend for a customer before assigning kit, no tenant-wide calendar of commitments, and no fleet occupancy view — so planning and conflict spotting happen outside the system.

## What Changes

- Introduce a first-class **Rental** as a tenant-scoped container: organisation, inclusive start/end dates, optional label. Devices are optional contents (empty rentals are valid).
- **BREAKING** (hire-company lending APIs): every appliance lending MUST belong to a rental. Floating lendings go away. Existing rows are backfilled (one rental per legacy lending, same org and dates).
- Device lines inherit the rental window. Early return / cancel of a single device does not delete the rental. Changing rental dates moves all assigned open lendings (rejected on overlap).
- Events stay independent: no rental↔event foreign key, no requirement either way.
- Display name: use the rental label when set; otherwise the organisation name. Do not snapshot the org name into the label.
- Add a Verwaltung calendar surface (tenant admins and platform admins with an active Verleiher): month + year views of rentals, plus a month fleet view (appliances on Y grouped by type, days on X).
- Organisation users keep the existing read-only Geräte-Ausleihen lists; they do not get the fleet calendar and cannot create rentals.

## Capabilities

### New Capabilities
- `rental-containers`: Tenant-scoped rental entity, membership of appliance lendings, CRUD, date inheritance, overlap rules, and legacy backfill.
- `rental-calendar`: Hire-company calendar/fleet UI under Verwaltung (month/year rentals + appliance×days month), access control, and display-name rules.

### Modified Capabilities
- _(none — appliance lending and edge sync keep working off `ApplianceLending`; there is no living spec for lending grouping today)_

## Impact

- **Cloud backend**: new `rentals` table + `rental_id` on `appliance_lendings`; Alembic migration and data backfill; tenant-admin CRUD and calendar-range list APIs; OpenAPI export + generated frontend types.
- **Cloud frontend**: Verwaltung nav item + `tenantAdminOnly` route; calendar/fleet views; rental create/edit/assign-device flows; i18n (de/en); existing org lending dialog and appliance “lend” form create or attach via a rental instead of posting orphan lendings.
- **Edge / Pi**: no protocol change — sync still keys off an open appliance lending for today.
- **Out of scope**: rental↔event linking; per-device date windows inside a rental; anonymous quantity holds (“2 Pis, any”); org-user rental creation; replacing the org-facing lending lists with a calendar.
