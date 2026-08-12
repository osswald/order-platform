## 1. Tests

- [x] 1.1 Add a `RentalsCalendar` test that the root element includes the shared `vq-page` page chrome class after mount

## 2. Implementation

- [x] 2.1 Add `vq-page` to the `RentalsCalendar` root and remove conflicting local padding from `.rentals-calendar` (keep flex/gap layout)
- [x] 2.2 Optionally align the title row with `vq-page-header` so header spacing matches other admin pages (keep HelpLink + Create actions)

## 3. Verification

- [x] 3.1 Run cloud frontend tests for `RentalsCalendar` (or full `npm test` in `cloud/frontend`)
- [x] 3.2 Run `./scripts/lint.sh --staged` (or full lint) before commit
