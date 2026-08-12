## 1. Schema and backfill

- [x] 1.1 Add `Rental` model and `appliance_lendings.rental_id` FK (nullable first) plus `hire_company` / `organisation` relationships
- [x] 1.2 Write Alembic migration: create `rentals`, add nullable `rental_id`, backfill one rental per existing lending (org + dates + org `hire_company_id`, null label), then set `rental_id` NOT NULL and indexes
- [x] 1.3 Add a migration test (or data-migration assertion) that leftover lendings without `rental_id` cannot exist after upgrade

## 2. Rental container API

- [x] 2.1 Write failing tests: create empty rental; optional label vs display_name fallback to org name; reject end before start; reject org outside tenant; list scoped to active Verleiher; org user forbidden
- [x] 2.2 Write failing tests: assign appliance inherits rental dates; overlap rejected; unassign planned deletes lending and keeps rental; return current keeps rental; delete empty OK; cancel planned-only OK; delete with current lending rejected; PATCH dates updates open lendings and rolls back on overlap
- [x] 2.3 Write failing tests: `POST /appliances/{id}/lendings` without a rental is rejected; create rental with `appliance_ids` is all-or-nothing
- [x] 2.4 Implement `/rentals` CRUD + assign/unassign/delete rules (tenant admin gate) and `display_name` on read schemas
- [x] 2.5 Implement range list `GET /rentals?from=&to=` and `GET /rentals/fleet?year=&month=` (non-hosted appliances grouped by type, open lendings only)
- [x] 2.6 Point hire-company lending writes at rentals (keep return/cancel segment rules); reject floating lending creates
- [x] 2.7 Export OpenAPI and regenerate `cloud/frontend` API types

## 3. Existing hire-company create UIs

- [x] 3.1 Update `OrganisationLendingDialog` to `POST /rentals` with dates + selected `appliance_ids` (transactional; no N independent lending posts)
- [x] 3.2 Update `Appliances.vue` lend form to create a one-device rental (org + dates + that appliance)
- [x] 3.3 Adjust appliance lending tests / frontend specs for the new create path
- [x] 3.4 Leave org-facing `ApplianceLendings.vue` read-only lists in the main menu unchanged (no calendar, no create)

## 4. Calendar / fleet UI

- [x] 4.1 Add `tenantAdminOnly` route (e.g. `/rentals`) and Verwaltung nav item next to Geräte (`nav.rentals`: Ausleihe / Lending), hidden for org users; platform admin requires active Verleiher
- [x] 4.2 Write frontend tests for access gating, display_name (label vs org), empty vs filled distinction, and fleet: assigned days occupied, empty rental absent, unassigned appliance still listed
- [x] 4.3 Implement rentals month view (bars with display name; empty rentals visually distinct)
- [x] 4.4 Implement rentals year view
- [x] 4.5 Implement fleet month view (Y: appliances grouped by type; X: days; occupancy from open lendings)
- [x] 4.6 Create rental from month/year (org + dates + optional label, appliances optional)
- [x] 4.7 Assign a free appliance from the fleet view (existing rental or create + assign)
- [x] 4.8 Add de/en i18n and a short help page for the calendar/fleet

## 5. Verification

- [x] 5.1 Run cloud backend tests (`cd cloud/backend && uv run pytest tests/ -v`)
- [x] 5.2 Run cloud frontend tests and typecheck
- [x] 5.3 Confirm existing edge/lending overlap tests still pass (no Pi protocol change)
- [x] 5.4 Run `./scripts/lint.sh` before commit
