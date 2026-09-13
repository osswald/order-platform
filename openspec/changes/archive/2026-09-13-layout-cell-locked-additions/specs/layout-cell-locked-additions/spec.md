## Purpose

Lets event layouts define one-tap variant buttons: a single base article with a locked set of Zusätze, sold the same way on every Pi POS layout without opening the additions sheet.

## ADDED Requirements

### Requirement: Layout cells may lock additions for a single article

The system SHALL allow an app-layout cell to store an ordered list of locked addition article ids (`locked_addition_ids`) in addition to its existing article and voucher fields. When `locked_addition_ids` is non-empty, the cell MUST reference exactly one base article and MUST NOT reference any voucher definition. Each locked addition id MUST be an addition article linked to that base article. Empty `locked_addition_ids` MUST preserve today’s multi-article and voucher cell behaviour.

#### Scenario: Combo cell persists locked additions

- **WHEN** an admin saves a layout cell with one base article, no vouchers, and one or more linked Zusätze selected as locked
- **THEN** configuration read and the edge event bundle include those ids on the cell in the configured order

#### Scenario: Locked additions rejected with multiple articles

- **WHEN** a client attempts to save a cell with more than one `article_id` and a non-empty `locked_addition_ids`
- **THEN** the configuration save is rejected with a validation error

#### Scenario: Locked additions rejected with vouchers

- **WHEN** a client attempts to save a cell that references any voucher definition and a non-empty `locked_addition_ids`
- **THEN** the configuration save is rejected with a validation error

#### Scenario: Locked addition must be linked to the base article

- **WHEN** a client attempts to save a locked addition id that is not linked to the cell’s single base article
- **THEN** the configuration save is rejected with a validation error

#### Scenario: Classic cells omit locked additions

- **WHEN** an admin saves a multi-article or voucher cell without locked additions
- **THEN** the cell is stored with an empty `locked_addition_ids` list and continues to work as before

### Requirement: Admin can configure locked Zusätze on qualifying cells

The cloud App-Layouts cell editor SHALL expose locked-Zusatz selection when the cell has exactly one selected base article and no vouchers. The selectable options MUST be the Zusätze linked to that base article. Changing the cell to multiple articles or any voucher MUST clear locked additions in the editor payload. Button label and color remain free-form as today.

#### Scenario: Locked Zusätze checklist appears for a single article

- **WHEN** the operator selects exactly one non-addition article and no vouchers in the cell dialog
- **THEN** the dialog shows that article’s linked Zusätze for locking

#### Scenario: Second article clears locked set in the editor

- **WHEN** the operator had locked Zusätze for one article and then selects a second article
- **THEN** the locked set is cleared before save

### Requirement: One-tap cart add for combo cells on all layouts

When an operator taps a layout cell with a non-empty `locked_addition_ids` on any Pi layout (waiter default or cash-register layout), the system SHALL add one cart line for the cell’s base article with each locked addition at quantity 1 and MUST NOT open the Zusätze sheet for that tap. Cells with empty `locked_addition_ids` MUST keep the existing multi-item picker and Zusätze-sheet behaviour.

#### Scenario: Combo tap skips Zusätze sheet

- **WHEN** the operator taps an enabled combo cell (one article, locked additions present)
- **THEN** the cart gains a line with those additions and no Zusätze sheet is shown

#### Scenario: Classic article with additions still opens the sheet

- **WHEN** the operator taps a cell with a single article that has additions and empty `locked_addition_ids`
- **THEN** the Zusätze sheet opens as today

#### Scenario: Waiter and register share combo behaviour

- **WHEN** the same combo cell appears on the waiter default layout and on a cash-register layout
- **THEN** tapping it produces the same one-tap cart behaviour in both flows

### Requirement: Combo button disabled when variant is not sellable

The Pi layout grid SHALL disable a combo cell when the base article is not sellable or when any locked addition is not sellable under the same sellability rules used for Zusätze selection. Disabled combo cells MUST NOT be tappable. Classic (non-combo) cell enablement MUST remain based on existing sellable articles / vouchers rules.

#### Scenario: Out-of-stock locked Zusatz disables the button

- **WHEN** a combo cell’s base article is sellable but one locked Zusatz is not sellable
- **THEN** the grid button is disabled

#### Scenario: All parts sellable enables the button

- **WHEN** the base article and every locked Zusatz on a combo cell are sellable
- **THEN** the grid button is enabled
