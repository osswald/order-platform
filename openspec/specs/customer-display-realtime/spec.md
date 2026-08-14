# customer-display-realtime Specification

## Purpose
Keeps the cash-register customer display in sync with cart and payment actions in near real time, with stable layout and clear SumUp / multi-pickup success UX.
## Requirements
### Requirement: Display state is pushed over WebSocket

The Pi SHALL expose a WebSocket for a cash register’s customer display. When display state is updated via the existing HTTP PUT, connected subscribers for that register SHALL receive the current payload promptly. On connect, the server SHALL send the current stored payload (or idle if none). The display client MAY retain a slow HTTP poll fallback only for reconnect safety; primary updates MUST come from the WebSocket while connected.

#### Scenario: Cart line change reaches display via socket

- **WHEN** the register POS updates display state (e.g. cart line added) via PUT
- **THEN** a customer display WebSocket subscribed to that register receives the updated payload without waiting for a fixed 1-second poll interval

#### Scenario: Snapshot on connect

- **WHEN** a customer display opens a WebSocket for a register that already has stored display state
- **THEN** the first message includes that stored payload

#### Scenario: Non-WebSocket clients still work

- **WHEN** a client only uses HTTP GET for display state
- **THEN** GET continues to return the current payload as today

### Requirement: Stable horizontal layout when lines overflow

When order lines exceed the visible area, horizontal positions of line labels and amounts MUST NOT shift due to scrollbar appearance or overflow. Prices MUST remain right-aligned in a stable column.

#### Scenario: Overflow does not shift prices left

- **WHEN** enough order lines are shown that the list becomes vertically scrollable
- **THEN** line amounts stay at the same horizontal alignment as before overflow began

### Requirement: SumUp connected waiting state

When the register chooses payment type `sumup_connected` and payment collection on the terminal is in progress, the customer display SHALL show the text `Bitte Anweisungen am Zahlungsterminal folgen.` (and MUST NOT show a Twint QR panel for that path).

#### Scenario: SumUp connected selected

- **WHEN** the cashier selects SumUp connected and terminal checkout is awaiting customer action
- **THEN** the customer display shows `Bitte Anweisungen am Zahlungsterminal folgen.`

### Requirement: Abort payment restores ordering (cart) view

When Twint payment UI is cancelled/dismissed without completing payment, or when SumUp connected collection fails or is aborted without a successful settlement, the customer display SHALL return to the ordering state showing the current open order lines and total (cart view). The display MUST NOT remain on the Twint QR panel or the SumUp terminal-waiting panel after such an abort.

#### Scenario: Twint cancelled

- **WHEN** Twint is shown on the customer display and the cashier cancels or dismisses Twint without paying
- **THEN** the customer display shows the ordering (cart) view again with the open order lines and total

#### Scenario: SumUp connected fails or is aborted

- **WHEN** the SumUp connected waiting state is shown and terminal collection fails or is aborted without settlement
- **THEN** the customer display shows the ordering (cart) view again with the open order lines and total

### Requirement: Success shows all pickup codes as badges

After successful payment for a cash-register order, the customer display SHALL show `Danke!`, then every pickup code for that order as individual badges (not a comma-separated string). If `pickup_codes` is empty, the single `pickup_code` (when present) SHALL be shown as one badge. When the production station name for a pickup is known, that badge SHALL show the station name on a line below the pickup code.

#### Scenario: Multiple pickup codes

- **WHEN** payment succeeds and the order has pickup codes `A1` and `A2`
- **THEN** the display shows `Danke!` and two badges labeled `A1` and `A2`

#### Scenario: Single pickup code

- **WHEN** payment succeeds and the order has one pickup code `A1`
- **THEN** the display shows `Danke!` and one badge labeled `A1`

#### Scenario: Station names under pickup codes

- **WHEN** payment succeeds and the order has pickup `A1` for station Grill and pickup `A2` for station Getränke
- **THEN** the `A1` badge shows `Grill` below the code
- **AND** the `A2` badge shows `Getränke` below the code

### Requirement: Success Abholbon copy is singular or plural

Below the pickup badges, the customer display SHALL show `Bitte Abholbon mitnehmen` when exactly one pickup code is shown, and `Bitte Abholbons mitnehmen` when two or more pickup codes are shown.

#### Scenario: Singular Abholbon

- **WHEN** the success screen shows exactly one pickup badge
- **THEN** the footer text is `Bitte Abholbon mitnehmen`

#### Scenario: Plural Abholbons

- **WHEN** the success screen shows two or more pickup badges
- **THEN** the footer text is `Bitte Abholbons mitnehmen`

