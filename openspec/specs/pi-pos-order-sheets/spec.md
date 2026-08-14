# pi-pos-order-sheets Specification

## Purpose
Keeps Pi POS order picker sheets visually consistent, makes the waiter/register TWINT QR payment surface fill the operator viewport, and keeps the customer-display TWINT QR inside its rounded panel.

## Requirements

### Requirement: Layout-cell picker matches additions picker type and controls

When an operator taps a layout cell that contains multiple sellable items, the **Position wählen** sheet SHALL use the same text size for option labels and prices as the **Zusätze** sheet uses for addition names and price hints, and SHALL use the same control height for option rows and for the footer **Abbrechen** button as the **Zusätze** sheet uses for its option rows and **Abbrechen** / **Übernehmen** buttons. The sheet MUST remain a bottom sheet (not a fullscreen takeover). Behavior of picking an item MUST NOT change.

#### Scenario: Option row type matches Zusätze

- **WHEN** the operator opens **Position wählen** with at least one item (for example Rivella variants)
- **THEN** each option label and price uses the same font size as addition names and price hints on **Zusätze**

#### Scenario: Option row height matches Zusätze

- **WHEN** the operator opens **Position wählen**
- **THEN** each tappable option row is the same height as a **Zusätze** addition row

#### Scenario: Footer Abbrechen matches Zusätze actions

- **WHEN** the operator opens **Position wählen**
- **THEN** **Abbrechen** is the same height and type size as **Abbrechen** and **Übernehmen** on **Zusätze**

### Requirement: TWINT QR sheet fills the viewport with actions at the bottom

When the operator is shown a TWINT QR code to complete payment, the TWINT sheet SHALL cover the full visible viewport of the Pi client (browser or Android WebView). Title, amount, and QR remain in the upper/middle area; **Fertig** and **Abbrechen** SHALL sit at the bottom of the sheet, above any system safe-area inset. Underlying POS chrome (including the Rest bar) MUST NOT remain visible beside or below the sheet. TWINT confirm/cancel behavior MUST NOT change.

#### Scenario: TWINT sheet covers the viewport in the browser

- **WHEN** the operator reaches TWINT payment in the Pi frontend in a browser
- **THEN** the TWINT sheet occupies the full visible height and the Rest bar / order grid are not visible around it

#### Scenario: TWINT actions sit at the bottom in the browser

- **WHEN** the TWINT QR sheet is open in a browser
- **THEN** **Fertig** is above **Abbrechen** at the bottom of the sheet

#### Scenario: TWINT sheet covers the viewport on Android

- **WHEN** the operator reaches TWINT payment in the Android WebView
- **THEN** the TWINT sheet occupies the full visible WebView height (after safe-area insets) and the Rest bar / order grid are not visible around it

#### Scenario: TWINT actions sit at the bottom on Android

- **WHEN** the TWINT QR sheet is open on Android
- **THEN** **Fertig** and **Abbrechen** sit at the bottom of the safe area and remain fully tappable

### Requirement: Waiter TWINT QR fills remaining space with margin

On the waiter/register TWINT sheet, the QR image SHALL scale to fill the space between the amount header and the action buttons, preserving aspect ratio, with visible margin on all sides so it does not touch the sheet edges, header, or **Fertig** / **Abbrechen** controls.

#### Scenario: QR uses the space between amount and actions

- **WHEN** the waiter or register TWINT sheet is open with a QR image
- **THEN** the QR is larger than a fixed 360px cap and fills the remaining column between the amount and the buttons without overlapping them

#### Scenario: QR keeps margin on all sides

- **WHEN** the waiter or register TWINT sheet is open with a QR image
- **THEN** the QR does not touch the left, right, top, or bottom of its region (margin remains around the image)

### Requirement: Customer-display TWINT QR stays inside the panel border

When the cash-register customer display shows TWINT with a QR image, the QR SHALL remain inside the rounded grey panel. It MUST NOT paint over the panel’s top, right, or bottom border or the rounded corners.

#### Scenario: Customer-display QR does not cover the grey border

- **WHEN** the customer display shows a TWINT QR
- **THEN** the rounded grey panel border remains fully visible around the QR card
