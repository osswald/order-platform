## 1. Keyboard helper (text-input sheets only)

- [x] 1.1 Add Vitest coverage for a `useKeyboardBottomInset` (or equivalent) composable: reports `0` when `visualViewport` is missing/unchanged; reports positive inset when viewport height shrinks
- [x] 1.2 Implement the composable and wire it only into sheets that contain text/number inputs

## 2. Shared Sammelrechnung name sheet

- [x] 2.1 Add/update tests: hub «Neue Sammelrechnung» opens in-app Name sheet (no `window.prompt`); confirm creates via API; assign-flow still uses the same Name UX
- [x] 2.2 Extract shared `CollectiveBillNameSheet` (or equivalent) matching current `PayTableActionsSheet` `new-name` step
- [x] 2.3 Use the shared sheet from `PayTableActionsSheet` and `OpenCollectiveBillsView`; apply keyboard bottom inset on that sheet
- [x] 2.4 Apply keyboard bottom inset to existing text-input sheets (`LinePositionSheet`, `LineDiscountSheet`, `OrderDiscountSheet`)

## 3. Shift cash-count without prompt

- [x] 3.1 Add/update tests for end-shift cash count using an in-app dialog (no `window.prompt`); cancel does not close the shift
- [x] 3.2 Implement shift-close amount dialog (mirror `ShiftOpenDialog` / promise pending pattern) and remove `window.prompt` from `useShiftSession`
- [x] 3.3 Grep Pi frontend for remaining `window.prompt` and ensure none remain

## 4. Verify

- [ ] 4.1 Run Pi frontend tests
- [ ] 4.2 Run lint for touched areas (`./scripts/lint.sh --staged` or full as appropriate)
