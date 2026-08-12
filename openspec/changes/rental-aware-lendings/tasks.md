## 1. Backend overlap and active-day resolution

- [ ] 1.1 Add failing tests for handover-day assign (end D + start D allowed), interior overlap still rejected, and return-day re-lend
- [ ] 1.2 Change `find_open_overlap` (and lend_check filters) to strict endpoint-touch semantics; update existing overlap tests
- [ ] 1.3 Add failing edge/active-lending tests for two open lendings covering today; implement prefer-arriving (`start_date == today`, else lowest id)
- [ ] 1.4 Apply the same active-day helper anywhere appliance “lent today” status is resolved

## 2. Backend lending DTOs and rental list filter

- [ ] 2.1 Add `organisation_id` query filter on `GET /rentals/` if missing; cover with a tenant-scoped test
- [ ] 2.2 Extend appliance and organisation lending response schemas with `rental_id` and `rental_display_name`; tests assert fields present
- [ ] 2.3 Export OpenAPI and regenerate cloud frontend API types; commit both artifacts

## 3. Calendar edit — add appliance

- [ ] 3.1 Add Vitest coverage for edit dialog add-appliance success and overlap error
- [ ] 3.2 Wire add-appliance UI in `RentalsCalendar.vue` edit mode to `POST /rentals/{id}/appliances` (create dialog stays without device picker)
- [ ] 3.3 Add de/en i18n strings for add-device actions and errors

## 4. Shared rental choice + appliance entry point

- [ ] 4.1 Extract or add a shared rental-choice flow (list org rentals newest-first, create-new, conflict disable/mark)
- [ ] 4.2 Replace appliance detail lend form to use rental choice then assign; toast on success; stay on page
- [ ] 4.3 Group appliance lending history by rental (foldable, newest first) with return/cancel actions inside groups
- [ ] 4.4 Vitest for pick-existing, create-new, and grouped history ordering

## 5. Organisation Geräte tab (Option X)

- [ ] 5.1 Show rental display name on lending rows; render past section; keep cancel planned
- [ ] 5.2 Update `OrganisationLendingDialog` to pick/create rental then multi-select appliances (no silent always-new rental without choice)
- [ ] 5.3 Vitest for past visibility, rental column, and lend-via-rental dialog behaviour
- [ ] 5.4 Align standalone `ApplianceLendings.vue` with rental display name if it shares the same DTOs (read-only consistency)

## 6. Verify

- [ ] 6.1 Run cloud backend pytest for rentals, appliance lending, and edge active-lending coverage
- [ ] 6.2 Run cloud frontend Vitest for calendar, appliances, organisations lend flows
- [ ] 6.3 Run `./scripts/lint.sh --staged` (or full) before commit
