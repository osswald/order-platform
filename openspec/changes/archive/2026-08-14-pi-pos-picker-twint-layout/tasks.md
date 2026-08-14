## 1. Tests

- [x] 1.1 Add a failing contract test: `.sheet--picker` option buttons inherit font size/family from the sheet (same as Zusätze labels)
- [x] 1.2 Add a failing contract test: `LayoutCellPickerSheet` footer **Abbrechen** uses shared `.btn` metrics (no extra 48px min-height)
- [x] 1.3 Add a failing contract test: `.twint-qr-sheet` fills the viewport (`inset: 0`, no `max-height: 70vh`) and keeps **Fertig** then **Abbrechen** in `.sheet-actions` at the end of the column flex
- [x] 1.4 Extend `androidSafeLayout.contract.test.ts` so TWINT still pads `--safe-top` / `--safe-bottom` after the height override
- [x] 1.5 Add a failing contract test: operator `.qr-image` fills `.qr-wrap` (`width`/`height` 100%, `object-fit: contain`, all-sides padding, no 360px cap)
- [x] 1.6 Add a failing contract test: customer-display `.twint-panel` clips overflow and `.qr-image` uses `max-height: 100%` (not `100dvh`)

## 2. Implementation

- [x] 2.1 In shared picker CSS, make `.sheet--picker .sheet-option-row__control--btn` inherit type and match Zusätze row padding/min-height
- [x] 2.2 Align `LayoutCellPickerSheet` footer **Abbrechen** with Zusätze `.btn` sizing
- [x] 2.3 Override `.twint-qr-sheet` so it is not capped by `.sheet { max-height: 70vh }`; keep column flex so actions stay at the bottom; preserve Android safe-area padding and hosted-demo width constraint
- [x] 2.4 Scale waiter/register TWINT QR to fill `.qr-wrap` with 1rem padding on all sides
- [x] 2.5 Keep customer-display TWINT QR inside the rounded grey panel (`overflow: hidden`, `max-height: 100%`)

## 3. Verify

- [x] 3.1 Make the new/updated Pi frontend contract tests pass
- [x] 3.2 Run Pi frontend tests for the touched area and `./scripts/lint.sh --staged` (or full lint) on changed files
