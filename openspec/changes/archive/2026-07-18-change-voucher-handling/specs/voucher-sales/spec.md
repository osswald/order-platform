## ADDED Requirements

### Requirement: Fixed-amount vouchers can be sold from register and waiter
The system SHALL accept `voucher_sale` lines for `fixed_amount` voucher definitions on both `order_source = "cash_register"` and `order_source = "waiter"` orders. Waiter orders containing voucher-sale lines SHALL follow the event payment mode (created `open` when unpaid under pay-later / pay-now, or routed to the instant collective bill under instant mode).

#### Scenario: Waiter open order with voucher sale
- **WHEN** a waiter posts an unpaid order that includes fixed-amount voucher-sale lines under pay-later
- **THEN** the order is created with `payment_status = "open"`

#### Scenario: Register open order with voucher sale
- **WHEN** a cash-register order with voucher-sale lines is posted without payments
- **THEN** the order is created open

#### Scenario: Instant waiter voucher sale lands on collective bill
- **WHEN** a waiter posts an order with voucher-sale lines under instant payment mode
- **THEN** the voucher-sale lines are associated with the instant collective bill like other lines

### Requirement: Voucher slips print at order submission
The system SHALL print one voucher slip per submitted voucher-sale unit when the order is successfully created, in the same submit window as station receipts. Later settlement or collective assignment MUST NOT print additional slips for those already submitted units.

#### Scenario: Mixed order prints vouchers at submit
- **WHEN** a register or waiter order containing voucher-sale lines is submitted successfully
- **THEN** one voucher slip is produced for each submitted voucher unit at submission time, alongside any station receipts for article lines

#### Scenario: Settlement does not reprint
- **WHEN** previously submitted voucher-sale units are later settled or assigned to a collective bill
- **THEN** no additional voucher print jobs or local voucher prints are created for those units

### Requirement: Waiter voucher printer destination
For waiter-origin voucher sales, the system SHALL print on the waiter device's configured Bluetooth printer when one is available. When no Bluetooth printer is configured, the system SHALL ask the waiter to choose a configured network printer before or during submission. When neither Bluetooth nor any network printer is available, the system SHALL warn the waiter and still allow the order to be submitted.

#### Scenario: Bluetooth printer configured
- **WHEN** a waiter submits an order with voucher-sale lines and the device has a configured Bluetooth printer
- **THEN** the voucher slips are printed on that Bluetooth printer without asking for a network printer

#### Scenario: No Bluetooth, network printers available
- **WHEN** a waiter submits an order with voucher-sale lines, no Bluetooth printer is configured, and one or more network printers are configured
- **THEN** the waiter is prompted to choose a network printer and the voucher slips are sent to the chosen printer

#### Scenario: No printers available
- **WHEN** a waiter submits an order with voucher-sale lines and neither Bluetooth nor network printers are available
- **THEN** the system warns that vouchers cannot be printed and the order submission still succeeds

### Requirement: Register voucher printer destination
For cash-register voucher sales, the system SHALL print voucher slips on the cash register's configured receipt printer using the existing network print path.

#### Scenario: Register voucher sale uses receipt printer
- **WHEN** a cash-register order with voucher-sale lines is submitted
- **THEN** voucher slips are queued for the register's configured receipt printer

### Requirement: Voucher-sale lines can be split-settled
The system SHALL treat open voucher-sale lines as selectable settleable groups. Partial settlement SHALL move only the selected voucher quantity (and selected articles) to the paid settlement, leave remaining voucher quantity open, and charge the server-priced face value for selected units (plus selected articles minus redemption credit). Settlement SHALL NOT create voucher print jobs for units already printed at submission.

#### Scenario: Pay some voucher units
- **WHEN** an open order has multiple units of a voucher sale and a settlement selects a subset of those units (with matching payment)
- **THEN** the selected units are marked paid / moved to the paid settlement and the original order remains open with the unpaid voucher quantity, without reprinting

#### Scenario: Pay articles without vouchers
- **WHEN** an open order contains both articles and voucher-sale lines and a settlement selects only articles
- **THEN** the articles are settled and voucher-sale lines remain open

#### Scenario: Full settlement of remaining vouchers
- **WHEN** all remaining open lines including voucher-sale units are settled
- **THEN** the order is fully paid and no additional voucher slips are printed for previously submitted units

### Requirement: Voucher-sale lines can be assigned to a collective bill
The system SHALL allow moving selected open voucher-sale lines (alone or with articles) from a register or table order onto an existing or newly named collective bill, using the same assignment semantics as article lines. Assignment SHALL NOT create voucher print jobs.

#### Scenario: Assign voucher sales to collective bill
- **WHEN** open voucher-sale lines on a register or table order are assigned to a collective bill
- **THEN** the lines appear on the bill's open order, the source order no longer holds those units, and no voucher slips are printed at assignment

#### Scenario: Settle vouchers on collective bill
- **WHEN** voucher-sale lines that were already printed at submission are later paid on a collective bill
- **THEN** payment succeeds without creating additional voucher print jobs for those units

### Requirement: Server-authoritative voucher sale price
The system SHALL price each `voucher_sale` line exclusively from the event's voucher definition `value_cents` for that `voucher_definition_uuid`. Client-supplied `unit_cents` MUST NOT change the charged amount. The system SHALL reject sale lines whose definition is missing or not `fixed_amount`.

#### Scenario: Client unit_cents ignored
- **WHEN** a create or settle request includes a voucher-sale line with `unit_cents` different from the definition value
- **THEN** the payable amount uses the definition `value_cents`

#### Scenario: Unknown definition rejected
- **WHEN** a voucher-sale line references an unknown `voucher_definition_uuid`
- **THEN** the system responds with 400

#### Scenario: Article-entitlement definition cannot be sold
- **WHEN** a voucher-sale line references an `article_entitlement` definition
- **THEN** the system responds with 400

### Requirement: Voucher redemption does not pay voucher sales
When settling a selection that includes voucher-sale lines and voucher redemptions, the system SHALL apply redemption credit only against selected article gross. Voucher-sale face value SHALL remain fully payable by ordinary payments.

#### Scenario: Mixed settle with redemption
- **WHEN** a settlement selects articles and voucher-sale units and includes a redemption
- **THEN** payable cents equal (article gross − redemption credit) + voucher-sale face value of selected units
