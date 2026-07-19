## MODIFIED Requirements

### Requirement: Register orders are created open without payments
The system SHALL accept `POST /v1/orders` with `order_source = "cash_register"` and no payments, creating the order with `payment_status = "open"`. Pickup code allocation, station print jobs, kitchen tickets, and customer pickup slips SHALL be created at order creation exactly as before. If the order contains voucher-sale lines, voucher slips SHALL also be printed at order creation. If payments are provided, the system SHALL keep the existing behavior (exact-amount validation, order born `paid`).

#### Scenario: Open creation
- **WHEN** a register order is posted without payments
- **THEN** the order is created with `payment_status = "open"`, a pickup code, and the same print jobs/kitchen tickets as a paid register order, and no payment receipt is created

#### Scenario: Paid creation still supported
- **WHEN** a register order is posted with payments equal to the order total
- **THEN** the order is created `paid` with a payment receipt, as today

#### Scenario: Voucher sale lines print on open creation
- **WHEN** a register order containing voucher-sale lines is posted without payments
- **THEN** the order is created open and voucher slips are printed at creation for each submitted voucher unit

### Requirement: Split settlement of a single order
The system SHALL provide `POST /v1/orders/{order_id}/settle-partial` accepting line selections (including voucher-sale groups), payments, and voucher redemptions, using the same settlement semantics as table partial settlement: paid lines move to a new paid order (or the original is marked paid on full settle), the payment amount MUST equal the selected total minus voucher credit applied to articles only, and a payment receipt is created. Open voucher-sale lines SHALL be settleable in whole or in part. Settlement MUST NOT create voucher print jobs for units already printed at order creation.

#### Scenario: Full settlement in one payment
- **WHEN** all open lines of a register order are selected and paid
- **THEN** the original order becomes `paid`, a payment receipt is created, and `remaining_cents` is 0

#### Scenario: Partial settlement
- **WHEN** a subset of lines is selected and paid
- **THEN** a new paid order holds the settled lines, the original order stays `open` with the remaining lines, and the pickup code stays on the original order

#### Scenario: Cash payment kicks the drawer
- **WHEN** a register order settlement includes a cash payment and the register has the cash drawer enabled
- **THEN** the cash drawer kick is enqueued at settlement time

#### Scenario: Voucher redemption at settlement
- **WHEN** voucher redemptions are included in the settlement
- **THEN** the payable amount is reduced by the voucher credit (against selected articles) and redemption records are stored on the paid order

#### Scenario: Partial voucher sale settlement without reprint
- **WHEN** a register order contains voucher-sale lines that were printed at creation and a partial selection that includes some voucher units is settled
- **THEN** the system accepts the settlement, leaves remaining voucher units open, and does not create additional voucher print jobs

### Requirement: Assign a register order to a collective bill
The system SHALL provide `POST /v1/orders/{order_id}/assign-collective` moving selected open lines of the order — including voucher-sale lines — to an existing or newly named collective bill, using the same semantics as table assignment. Assignment SHALL NOT create voucher print jobs.

#### Scenario: Assign all lines
- **WHEN** all open lines of a register order are assigned to a collective bill
- **THEN** the lines are appended to the bill's open order and the register order no longer has open lines

#### Scenario: Assign voucher-sale lines
- **WHEN** selected voucher-sale lines on a register order are assigned to a collective bill
- **THEN** those lines move to the bill's open order without printing voucher slips
