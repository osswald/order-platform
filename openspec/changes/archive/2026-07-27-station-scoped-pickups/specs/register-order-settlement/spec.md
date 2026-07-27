## MODIFIED Requirements

### Requirement: Register orders are created open without payments
The system SHALL accept `POST /v1/orders` with `order_source = "cash_register"` and no payments, creating the order with `payment_status = "open"`. Pickup allocation (one code per production-station group with article lines), station print jobs, kitchen tickets, and customer pickup slips SHALL be created at order creation. If the order contains voucher-sale lines, voucher slips SHALL also be printed at order creation. If payments are provided, the system SHALL keep the existing behavior (exact-amount validation, order born `paid`).

#### Scenario: Open creation
- **WHEN** a register order is posted without payments
- **THEN** the order is created with `payment_status = "open"`, pickup code(s) for its station groups, and the same print jobs/kitchen tickets as a paid register order, and no payment receipt is created

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
- **THEN** a new paid order holds the settled lines, the original order stays `open` with the remaining lines, and all station pickup codes stay on the original order

#### Scenario: Cash payment kicks the drawer
- **WHEN** a register order settlement includes a cash payment and the register has the cash drawer enabled
- **THEN** the cash drawer kick is enqueued at settlement time

#### Scenario: Voucher redemption at settlement
- **WHEN** voucher redemptions are included in the settlement
- **THEN** the payable amount is reduced by the voucher credit (against selected articles) and redemption records are stored on the paid order

#### Scenario: Partial voucher sale settlement without reprint
- **WHEN** a register order contains voucher-sale lines that were printed at creation and a partial selection that includes some voucher units is settled
- **THEN** the system accepts the settlement, leaves remaining voucher units open, and does not create additional voucher print jobs

### Requirement: Open register orders are listed for resumption
The system SHALL provide `GET /v1/registers/{register_uuid}/open-orders?event_id=` returning open cash-register orders of that register (order id, pickup code(s), total cents, item count, created_at) so the register UI can resume payment. Each open order SHALL appear as a single row that includes all pickup codes allocated for that order.

#### Scenario: Open order listed
- **WHEN** a register order was created open and not yet settled
- **THEN** it appears in that register's open-orders list with its pickup code(s) and open total

#### Scenario: Settled order not listed
- **WHEN** a register order has been fully settled or fully assigned
- **THEN** it no longer appears in the open-orders list

#### Scenario: Multi-station open order one row
- **WHEN** an open register order has multiple station pickup codes
- **THEN** the open-orders list contains exactly one row for that order
- **AND** the row exposes all of those pickup codes
