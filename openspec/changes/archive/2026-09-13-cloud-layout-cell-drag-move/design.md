## Context

See proposal.md for motivation. Cloud event Layouts are edited in `EventConfigLayoutsSection.vue`: a CSS grid of buttons for every `{row,col}` in `grid_width` × `grid_height`. Filled cells live in `layouts[].cells` with `row`/`col` and content; empty slots are rendered placeholders with no stored cell (or no meaningful data). Click opens a dialog; there is no drag today. Persistence is the existing configuration dirty autosave — no API shape change.

## Goals / Non-Goals

**Goals:**

- Pointer-based move of a filled cell to an empty slot by rewriting `row`/`col` in local state.
- Clear click-vs-drag separation so edit-on-click remains reliable.
- Occupancy checks aligned with existing `cellHasData` semantics.
- Tests covering move success, occupied reject, empty non-draggable, and click-still-edits.

**Non-Goals:**

- Swap or overwrite occupied cells.
- Pi POS or edge runtime rearrange.
- New backend fields, OpenAPI regen, or DnD library dependency.
- Palette-to-grid compose, multi-cell span/resize.
- Dedicated first-event wizard work (wizard only benefits if it already mounts this same section unchanged).

## Decisions

### 1. Pointer Events + movement threshold (not HTML5 DnD, not a library)

- **Choice:** `pointerdown` / `pointermove` / `pointerup` with `setPointerCapture`, start drag after ~6–8px movement; otherwise treat as click → `openCellDialog`.
- **Why:** Same element must support click and drag; HTML5 DnD is awkward with `<button>` and touch; no existing DnD dependency in cloud frontend.
- **Alternatives:** HTML5 `draggable`; VueUse / SortableJS — rejected as heavier than needed for a fixed CSS grid.

### 2. Occupancy = existing `cellHasData`

- **Choice:** A slot is occupied (not a drop target; is a drag source) when `cellHasData` is true (label, articles, vouchers, or non-default color).
- **Why:** Matches how the editor already thinks about “something is there,” including decorative label/color cells that aren’t sellable yet.
- **Alternatives:** Only `layoutCellHasContent` (articles/vouchers) — would allow dropping onto label-only cells and overwriting them; rejected per “block occupied.”

### 3. Move implementation = update coordinates on the existing cell object

- **Choice:** On valid drop, set `cell.row` / `cell.col` to the target (or remove+reinsert equivalent). Do not clone content into a new object unless needed for Vue reactivity — prefer mutating the found cell in `lo.cells`.
- **Why:** Minimal change; autosave already watches layouts; payload builders already send `row`/`col`.

### 4. Illegal drop feedback = cursor / CSS only

- **Choice:** `not-allowed` / no highlight on occupied targets; no toast.
- **Why:** Quiet UX; reject is immediate and reversible (cell stays put).
- **Alternatives:** Toast on every illegal drop — noisy during exploration.

### 5. Affordance = grab cursor on filled cells only

- **Choice:** `cursor: grab` / `grabbing` on filled cells; empty cells keep default click affordance.
- **Why:** Signals draggability without adding a handle that fights the click target.

### 6. Scope surface = event config Layouts section only

- **Choice:** Implement in `EventConfigLayoutsSection` (and unit tests). No Pi components.
- **Why:** Proposal scope; POS grid is read-only for selling.

## Risks / Trade-offs

- **[Click accidentally becomes drag]** → Use a small pixel threshold; only filled cells arm drag; do not open dialog after a completed drag.
- **[Touch / trackpad flakiness]** → Prefer Pointer Events + capture; smoke-test on trackpad; keep threshold modest.
- **[Autosave during drag]** → Prefer committing the move only on successful `pointerup` drop so intermediate positions don’t spam saves; single mutation at end is enough for dirty watch.
- **[Visual ghost complexity]** → Start with source opacity + target highlight; add a floating ghost only if needed for clarity.

## Migration Plan

- Frontend-only; ship behind normal PR. No data migration. Rollback = revert the frontend change; stored layouts remain valid either way.

## Open Questions

- None that block implementation; pixel threshold and highlight styling can be tuned in UI review without changing requirements.
