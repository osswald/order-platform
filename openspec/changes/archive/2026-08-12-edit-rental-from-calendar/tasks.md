## 1. Tests first

- [x] 1.1 Add frontend tests for month/year bar click opening edit (not create) and empty day/track still creating
- [x] 1.2 Add frontend tests for edit dialog: organisation read-only, save label/dates calls PATCH, delete shown only when allowed, unassign/return call the lending delete endpoint
- [x] 1.3 Confirm backend already covers PATCH label/dates, delete rules, and org immutability (add a focused test only if org-change rejection is not already implied by `RentalUpdate` schema)

## 2. Calendar edit UI

- [x] 2.1 Wire month chips and year bars to `openEdit(id)` with `stopPropagation`; keep empty day/year-track create behaviour; leave fleet clicks unchanged
- [x] 2.2 Implement edit mode dialog: load `GET /rentals/{id}`, show org read-only, editable label/dates, save via `PATCH /rentals/{id}`, surface overlap errors
- [x] 2.3 List lendings with unassign (planned) / return (current) via `DELETE /rentals/{id}/lendings/{lending_id}`; refresh dialog after success
- [x] 2.4 Add delete/cancel action gated by existing delete rules; close dialog and reload calendar on success; show API error when blocked
- [x] 2.5 Optional low-cost “add appliance” select in edit dialog using `POST /rentals/{id}/appliances` (skip if it bloats the first cut; device unassign/return is required)

## 3. i18n and help

- [x] 3.1 Add de/en strings for edit title, delete/cancel, device actions, and save/delete errors
- [x] 3.2 Update rental-calendar help (de/en) to mention click-to-edit, delete rules, and org immutability

## 4. Verification

- [x] 4.1 Run cloud frontend tests and typecheck
- [x] 4.2 Run relevant cloud backend rental tests if any were added/touched
- [x] 4.3 Run `./scripts/lint.sh` before commit
