# register-order-settlement Specification

## Purpose
Define how cash-register orders are created open, settled (fully, partially, or via vouchers), assigned to collective bills, and resumed from the register UI — unifying the register payment flow with the waiter table-settlement flow.

## Requirements
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

### Requirement: Order-scoped settlement summary
The system SHALL provide `GET /v1/orders/{order_id}/summary` returning the open line groups of a single order in the same shape as the table and collective-bill summaries.

#### Scenario: Summary of an open register order
- **WHEN** the summary of an open register order is requested
- **THEN** the response contains line groups with quantities, unit prices, and total cents for the order's unpaid lines

#### Scenario: Order not open
- **WHEN** the summary of a paid or unknown order is requested
- **THEN** the system responds with 404

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

### Requirement: Open register orders are listed for resumption
The system SHALL provide `GET /v1/registers/{register_uuid}/open-orders?event_id=` returning open cash-register orders of that register (order id, pickup code, total cents, item count, created_at) so the register UI can resume payment.

#### Scenario: Open order listed
- **WHEN** a register order was created open and not yet settled
- **THEN** it appears in that register's open-orders list with its pickup code and open total

#### Scenario: Settled order not listed
- **WHEN** a register order has been fully settled or fully assigned
- **THEN** it no longer appears in the open-orders list

### Requirement: Register payment happens on a payment screen after order creation
The register UI SHALL create the order first (no payment collection on the order screen) and then show a payment screen with per-line split payment, voucher redemption, and collective-bill assignment. Voucher redemption SHALL NOT be available on the register order screen. Leaving the payment screen SHALL keep the order open and return to the register hub, which lists open orders.

#### Scenario: Order screen submits without payment
- **WHEN** the cashier submits the cart on the register order screen
- **THEN** the order is created open and the payment screen for that order is shown

#### Scenario: Payment screen parity with waiter settle screen
- **WHEN** the payment screen is shown
- **THEN** it offers line-selection split payment, voucher redemption, and collective-bill assignment, like the waiter table settle screen

#### Scenario: Abandoning payment
- **WHEN** the cashier navigates back from the payment screen without paying
- **THEN** the order remains open and is listed on the register hub for later payment

### Requirement: Register hub exposes Sammelrechnungen like the waiter hub
The register UI SHALL provide a Sammelrechnungen action on the cash register hub that opens the open collective-bills list for the current event, using the same list/create/open capabilities as the waiter hub entry.

#### Scenario: Open collective bills from register hub
- **WHEN** the cashier taps Sammelrechnungen on the register hub
- **THEN** the open collective-bills screen is shown for the current event

#### Scenario: Create collective bill from register context
- **WHEN** the cashier creates a new Sammelrechnung after entering from the register hub (and the event is not in instant payment mode)
- **THEN** the bill is created and the settle screen for that bill is shown, as for waiters

### Requirement: Collective-bill navigation returns to the register hub
When the open collective-bills flow is entered from the register hub, back navigation SHALL return to that register hub (not the waiter hub). Leaving a collective settle screen SHALL return to the open collective-bills list while preserving register return context.

#### Scenario: Back from collective list to register hub
- **WHEN** the cashier opens Sammelrechnungen from the register hub and then navigates back from the list
- **THEN** the register hub for the same register is shown

#### Scenario: Back from collective settle keeps register context
- **WHEN** the cashier opens a Sammelrechnung from the register-entered list and navigates back from settle
- **THEN** the open collective-bills list is shown and a further back still returns to the register hub
