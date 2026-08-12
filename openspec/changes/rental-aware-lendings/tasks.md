## 1. Backend overlap and active-day resolution

- [x] 1.1 Add failing tests for handover-day assign (end D + start D allowed), interior overlap still rejected, and return-day re-lend
- [x] 1.2 Change `find_open_overlap` (and lend_check filters) to strict endpoint-touch semantics; update existing overlap tests
- [x] 1.3 Add failing edge/active-lending tests for two open lendings covering today; implement prefer-arriving (`start_date == today`, else lowest id)
- [x] 1.4 Apply the same active-day helper anywhere appliance “lent today” status is resolved

## 2. Backend lending DTOs and rental list filter

- [x] 2.1 Add `organisation_id` query filter on `GET /rentals/` if missing; cover with a tenant-scoped test
- [x] 2.2 Extend appliance and organisation lending response schemas with `rental_id` and `rental_display_name`; tests assert fields present
- [x] 2.3 Export OpenAPI and regenerate cloud frontend API types; commit both artifacts

## 3. Calendar edit — add appliance

- [x] 3.1 Add Vitest coverage for edit dialog add-appliance success and overlap error
- [x] 3.2 Wire add-appliance UI in `RentalsCalendar.vue` edit mode to `POST /rentals/{id}/appliances` (create dialog stays without device picker)
- [x] 3.3 Add de/en i18n strings for add-device actions and errors

## 4. Shared rental choice + appliance entry point

- [x] 4.1 Extract or add a shared rental-choice flow (list org rentals newest-first, create-new, conflict disable/mark)
- [x] 4.2 Replace appliance detail lend form to use rental choice then assign; toast on success; stay on page
- [x] 4.3 Group appliance lending history by rental (foldable, newest first) with return/cancel actions inside groups
- [x] 4.4 Vitest for pick-existing, create-new, and grouped history ordering

## 5. Organisation Geräte tab (Option X)

- [x] 5.1 Show rental display name on lending rows; render past section; keep cancel planned
- [x] 5.2 Update `OrganisationLendingDialog` to pick/create rental then multi-select appliances (no silent always-new rental without choice)
- [x] 5.3 Vitest for past visibility, rental column, and lend-via-rental dialog behaviour
- [x] 5.4 Align standalone `ApplianceLendings.vue` with rental display name if it shares the same DTOs (read-only consistency)

## 6. Verify

- [ ] 6.1 Run cloud backend pytest for rentals, appliance lending, and edge active-lending coverage
- [ ] 6.2 Run cloud frontend Vitest for calendar, appliances, organisations lend flows
- [ ] 6.3 Run `./scripts/lint.sh --staged` (or full) before commit
