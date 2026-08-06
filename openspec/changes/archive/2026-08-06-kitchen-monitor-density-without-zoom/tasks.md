## 1. Tests first

- [x] 1.1 Update Vitest: ≥4 columns at **1024px true width** (no zoom layout helper); drop or rewrite `kitchenLayoutWidthForViewport` / `KITCHEN_DISPLAY_ZOOM` expectations
- [x] 1.2 Update contract test: kitchen monitor MUST NOT use `--kitchen-zoom` / compensating `calc(100% / …)` zoom size; assert normal `100dvh` (or equivalent) fill

## 2. Remove zoom; densify columns

- [x] 2.1 Remove CSS zoom and compensating width/height from `KitchenMonitorView`; restore normal viewport fill
- [x] 2.2 Lower `KITCHEN_MIN_COLUMN_WIDTH_PX` so `computeKitchenColumnLayout(1024)` yields ≥4 columns (keep `KITCHEN_ORDER_GAP_PX` synced to CSS)
- [x] 2.3 Remove unused `KITCHEN_DISPLAY_ZOOM` / `kitchenLayoutWidthForViewport` if nothing else needs them

## 3. Verify

- [x] 3.1 Run Pi frontend tests and lint for touched areas
- [x] 3.2 Manual QA: Bestellungen ~4 columns on tablet; Produkte wrap under Chrome page zoom; header controls fully visible on Android + desktop
