# pi-android-text-input-sheets Specification

## Purpose
Replace browser `window.prompt` dialogs in the Pi waiter/register frontend with in-app sheets/dialogs, and keep soft-keyboard-aware bottom spacing limited to sheets that contain text or numeric inputs.

## Requirements

### Requirement: Sammelrechnung naming uses an in-app sheet

The Pi frontend SHALL collect a new Sammelrechnung name through an in-app bottom sheet (Name field and primary action). It MUST NOT use `window.prompt` (or other browser JS dialogs) for this name entry.

#### Scenario: Create from Sammelrechnungen list

- **WHEN** the operator taps «Neue Sammelrechnung» on the open collective-bills list and the event is not in instant payment mode
- **THEN** an in-app sheet asks for the Name (with a placeholder such as «z. B. Personal»)
- **AND** confirming with a non-empty name creates the bill via the existing create API and continues to the settlement screen as today
- **AND** no WebView/system JS prompt dialog is shown

#### Scenario: Create while assigning open positions

- **WHEN** the operator chooses Sammelrechnung → «Neue Sammelrechnung» from the open-positions actions sheet
- **THEN** the same Name-entry sheet UX is shown as for list create
- **AND** confirming creates/assigns with the entered name using the existing assign-collective semantics

### Requirement: Pi frontend does not use window.prompt

The Pi waiter/register frontend SHALL NOT call `window.prompt` for operator input. Shift cash-count on end-shift SHALL use an in-app amount dialog consistent with shift open.

#### Scenario: End shift cash count

- **WHEN** the operator ends a shift that requires counted cash
- **THEN** an in-app dialog collects the counted amount (prefilled with the expected wallet amount when available)
- **AND** cancel leaves the shift open without closing
- **AND** no `window.prompt` dialog is shown

### Requirement: Soft keyboard does not cover text-input sheet fields

Bottom sheets that contain text or numeric `<input>` fields SHALL keep the focused input and primary actions visible above the soft keyboard on Android (and other mobile viewports that shrink `visualViewport`). Sheets without text inputs MUST NOT receive this keyboard lift behavior as part of this change.

#### Scenario: Name field visible while typing

- **WHEN** the Sammelrechnung Name sheet is open and the soft keyboard is shown
- **THEN** the Name field and the primary create/assign action remain visible above the keyboard

#### Scenario: Line comment sheet visible while typing

- **WHEN** a line position/comment or discount sheet with a text/number input is open and the soft keyboard is shown
- **THEN** the active input and sheet actions remain visible above the keyboard

#### Scenario: Non-input sheets unchanged

- **WHEN** a bottom sheet without text inputs is open (for example payment type picker or receipt prompt)
- **THEN** its layout is not altered by the keyboard-avoidance mechanism introduced for text-input sheets
