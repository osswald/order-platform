# cloud-layout-cell-drag-move Specification

## Purpose

Lets cloud operators reposition filled POS layout cells onto empty grid slots by drag-and-drop without losing click-to-edit or risking overwrite of occupied cells.

## Requirements

### Requirement: Move filled layout cell onto empty slot

In the cloud event configuration Layouts grid, the system SHALL allow an operator to drag a filled cell and drop it onto an empty grid slot. On a successful drop, the system MUST update that cell’s `row` and `col` to the target slot and MUST preserve the cell’s label, color, articles, and vouchers. The move MUST use the same local layout model that existing dirty autosave already persists.

#### Scenario: Drag filled cell onto empty slot

- **WHEN** an operator drags a filled layout cell and drops it on an empty grid slot
- **THEN** the cell appears at the target slot with the same content
- **AND** the source slot is empty
- **AND** the layout is marked dirty for autosave like any other layout edit

#### Scenario: Drop on same slot is a no-op

- **WHEN** an operator drops a filled cell onto its current slot
- **THEN** the cell remains at that slot
- **AND** no content is lost

### Requirement: Reject drops onto occupied cells

The system MUST NOT move a dragged cell onto a slot that already has layout content. Occupied means the slot has content under the same definition the layout editor already uses for “cell has data” (label, articles, vouchers, or non-default color). The system MUST NOT swap cells and MUST NOT overwrite the target cell.

#### Scenario: Drop onto occupied cell is rejected

- **WHEN** an operator drops a filled cell onto a slot that already has content
- **THEN** the dragged cell remains at its original slot
- **AND** the target cell is unchanged

#### Scenario: Empty cells are not drag sources

- **WHEN** an operator attempts to drag an empty grid slot
- **THEN** no drag move starts

### Requirement: Click still opens cell editor

A short click (pointer press and release without a drag past the movement threshold) on a grid cell SHALL continue to open the existing cell edit dialog. Starting or completing a drag move MUST NOT open that dialog.

#### Scenario: Click opens edit dialog

- **WHEN** an operator clicks a grid cell without dragging past the movement threshold
- **THEN** the cell edit dialog opens as before

#### Scenario: Drag does not open edit dialog

- **WHEN** an operator drags a filled cell (movement past the threshold) and releases
- **THEN** the cell edit dialog does not open as a result of that drag
