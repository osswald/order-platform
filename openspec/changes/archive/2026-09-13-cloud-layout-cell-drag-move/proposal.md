## Why

Operators rearrange POS layout buttons by deleting and recreating cells or re-entering content at a new grid position. Moving a configured button to an empty slot should be a direct drag gesture in the cloud event Layouts editor, without changing Pi runtime behavior or the layout data model.

## What Changes

- In the cloud event configuration Layouts grid, operators can drag a filled cell onto an empty grid slot to move it (update `row`/`col` only).
- Drops onto occupied cells are rejected (no swap, no overwrite).
- A short click on a cell still opens the existing edit dialog; drag uses a movement threshold so click and drag do not fight.
- Empty cells are not drag sources.
- Scope is cloud admin only (event config Layouts tab). No Pi POS changes, no backend schema/API changes, no first-event wizard work unless that UI already shares this grid component unchanged.

## Capabilities

### New Capabilities

- `cloud-layout-cell-drag-move`: Cloud event Layouts grid supports move-into-empty via drag-and-drop while preserving click-to-edit.

### Modified Capabilities

- (none)

## Impact

- **Cloud frontend**: `EventConfigLayoutsSection.vue` (and tests) — pointer/drag interaction on the layout preview grid; local `layouts[].cells` mutation; existing dirty autosave picks up moves.
- **Backend / OpenAPI / Pi**: none expected (same cell payload shape).
- **Dependencies**: no new DnD library required (Pointer Events or HTML5 drag within the existing Vue/Vuetify stack).
