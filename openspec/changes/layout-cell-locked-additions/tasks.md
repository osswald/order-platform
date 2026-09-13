## 1. Cloud data model and API

- [x] 1.1 Add failing cloud backend tests for `locked_addition_ids` on layout cells (persist/round-trip, reject multi-article + locks, reject vouchers + locks, reject unlinked addition) and verify they fail before implementation
- [x] 1.2 Add schema patch / M2M table for cell locked additions with sort order and verify migration applies on cloud backend startup
- [x] 1.3 Extend `LayoutCellIn` / `LayoutCellRead`, configuration serialize/replace, and validation to enforce combo rules; verify the tests from 1.1 pass
- [x] 1.4 Include `locked_addition_ids` in edge event bundle layout cells (default `[]`) and verify bundle/export tests cover the field
- [x] 1.5 Run `python cloud/backend/scripts/export_openapi.py` and `cd cloud/frontend && npm run generate:api-types`; verify `openapi.json` and `src/types/api.generated.ts` include `locked_addition_ids`

## 2. Cloud admin UI

- [x] 2.1 Add failing frontend coverage for cell-dialog combo rules: show locked-Zusatz checklist for one article / no vouchers; clear locks when a second article or voucher is selected (follow existing frontend test patterns)
- [x] 2.2 Wire `EventLayoutCellLocal`, `eventConfigLayoutsPayload.ts`, and `EventConfigLayoutsSection.vue` to edit/save `locked_addition_ids`; verify 2.1 tests pass and a save payload includes the field

## 3. Pi POS behaviour

- [x] 3.1 Add failing Pi frontend tests for combo `cellEnabled` (disabled when base or any locked Zusatz unsellable; enabled when all sellable) and for one-tap cart add that skips the Zusätze sheet
- [x] 3.2 Extend layout cell types/helpers to read `locked_addition_ids` (default `[]`) and update `EventLayoutGrid.vue` enablement for combo cells; verify sellability tests from 3.1 pass
- [x] 3.3 Update `OrderView.vue` and `RegisterOrderView.vue` so a combo cell tap adds the line with locked additions at qty 1 and does not open `AdditionsPickerSheet`; verify one-tap tests from 3.1 pass and classic cells still open the sheet when locks are empty

## 4. Verification

- [x] 4.1 Run cloud backend tests for the touched layout/config areas and verify they pass
- [x] 4.2 Run Pi frontend tests for layout/order helpers and views and verify they pass
- [x] 4.3 Run `./scripts/lint.sh` (or `./scripts/lint.sh --staged`) before commit and verify it exits 0
- [x] 4.4 Run `npx openspec validate layout-cell-locked-additions --strict` and verify the change validates
