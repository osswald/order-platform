## ADDED Requirements

### Requirement: Ticket print actions remain readable within the ticket column

Kitchen order tickets SHALL show **Teildruck** and **Komplettdruck** action controls with their full labels visible inside the ticket card width on WebKit/Safari and Chromium, without relying on overflow outside the ticket (including when the ticket is near the kitchen minimum column width).

#### Scenario: Both action labels visible in order view

- **WHEN** the kitchen monitor shows an open order ticket in Bestellungen view
- **THEN** the ticket footer SHALL display a Teildruck control whose label text is visible
- **AND** the ticket footer SHALL display a Komplettdruck control whose label text is visible
- **AND** both controls SHALL fit within the ticket’s visible bounds (not clipped to empty outline/fill only)

#### Scenario: Action row allows buttons to shrink below intrinsic label width

- **WHEN** ticket action buttons are laid out in a two-column row inside a constrained ticket width
- **THEN** the layout SHALL permit each action button to shrink below its intrinsic nowrap content width (e.g. via `minmax(0, …)` tracks and `min-width: 0` on the buttons)
- **AND** long labels MAY wrap onto multiple lines rather than forcing horizontal overflow

### Requirement: Ticket print action behavior unchanged

Changing action-button presentation SHALL NOT alter print semantics: Teildruck remains disabled until at least one line is selected; Komplettdruck remains available when the ticket is not busy; activating each control SHALL still emit the existing partial/complete print actions.

#### Scenario: Teildruck disabled without selection

- **WHEN** no line on the ticket has a selected quantity greater than zero
- **AND** the ticket is not busy
- **THEN** the Teildruck control SHALL be disabled
- **AND** the Komplettdruck control SHALL remain enabled

#### Scenario: Actions emit print intents

- **WHEN** the operator activates Teildruck with a valid selection
- **THEN** the ticket SHALL emit the partial-print action
- **WHEN** the operator activates Komplettdruck
- **THEN** the ticket SHALL emit the complete-print action
