## 1. Tests first

- [x] 1.1 Extend `EventConfigLayoutsSection.spec.ts` with helpers to simulate pointer drag (down → move past threshold → up on target)
- [x] 1.2 Assert filled cell dropped on empty slot updates `row`/`col` and preserves label/articles/vouchers; source slot empty
- [x] 1.3 Assert drop onto occupied slot leaves both cells unchanged
- [x] 1.4 Assert empty slot does not start a move
- [x] 1.5 Assert short click still opens the cell edit dialog; completed drag does not open it

## 2. Move logic

- [x] 2.1 Add a pure helper (or section-local function) to move a cell to an empty `{row,col}` using `cellHasData` occupancy; reject occupied / out-of-bounds / same-slot no-op
- [x] 2.2 Wire the helper into `EventConfigLayoutsSection` so a successful move mutates `layouts[].cells` once on drop (dirty autosave picks it up)

## 3. Pointer UX

- [x] 3.1 Implement Pointer Events on filled grid cells with movement threshold; keep click → `openCellDialog` when below threshold
- [x] 3.2 Visual feedback: grab/grabbing cursor on filled cells; source opacity and empty-target highlight while dragging; `not-allowed` on occupied (no toast)
- [x] 3.3 Ensure drag does not open the cell dialog on pointerup after a move attempt

## 4. Verify

- [x] 4.1 Run cloud frontend tests for the layouts section (`npm test` / Vitest targeting the spec file)
- [x] 4.2 Run lint for touched cloud frontend files (`./scripts/lint.sh --staged` or full as appropriate)
