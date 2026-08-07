## Purpose

Define the public guest self-order runtime: QR entry, prepaid per-phone orders bound to a table for routing, stay-at-table confirmation, stock visibility, Pi-offline soft gate, and the cloud paid-order inbox awaiting Pi pull.

## ADDED Requirements

### Requirement: Guest orders are prepaid before venue delivery

The system MUST accept guest checkouts only through the cloud guest ordering surface. A guest order MUST reach the Pi paid-order inbox only after payment has succeeded. The system MUST NOT create kitchen, print, or local Pi order work for unpaid guest carts.

#### Scenario: Payment required before inbox

- **WHEN** a guest completes a cart but payment has not succeeded
- **THEN** the order MUST NOT appear in the Pi pull inbox

#### Scenario: Paid order enters inbox

- **WHEN** guest payment for an order succeeds
- **THEN** the order MUST be stored as paid and pending Pi pull

### Requirement: One phone creates one guest order

The system MUST treat each guest checkout as an independent order. Multiple guests ordering at the same table MUST produce separate orders. The table number from the QR MUST be used for routing and stay-at-table messaging only, not for merging carts or shared payment.

#### Scenario: Two guests at one table

- **WHEN** two guest devices complete separate paid checkouts for the same table number
- **THEN** the system MUST create two distinct paid guest orders for that table

### Requirement: Guest cancel only before payment

The system MUST allow a guest to abandon or cancel an order only while it is not paid. After payment succeeds, the guest MUST NOT be able to cancel the order through the guest surface.

#### Scenario: Cancel before pay

- **WHEN** a guest cancels or abandons a draft or awaiting-payment order
- **THEN** the order MUST NOT be delivered to the Pi

#### Scenario: No guest cancel after pay

- **WHEN** a guest order is paid
- **THEN** guest APIs MUST reject cancel requests for that order

### Requirement: Stay-at-table confirmation

After successful payment, the guest surface MUST show a confirmation that the order is being prepared for their table (stay-at-table service). The confirmation MUST include the table number from the QR.

#### Scenario: Confirmation after pay

- **WHEN** guest payment succeeds for table N
- **THEN** the guest UI MUST show a stay-at-table confirmation that references table N

### Requirement: Guest catalog stock visibility

For the guest menu catalog, the system MUST always show articles that are not stock-monitored. For monitored articles, the system MUST hide an article when cloud `in_stock` is below the event’s configured hide-below threshold. The default threshold MUST be 15 when unset.

#### Scenario: Unmonitored always visible

- **WHEN** a guest-menu article is not stock-monitored
- **THEN** it MUST appear in the guest catalog regardless of `in_stock`

#### Scenario: Monitored below threshold hidden

- **WHEN** a guest-menu article is stock-monitored and `in_stock` is less than the configured hide-below threshold
- **THEN** it MUST NOT appear as available in the guest catalog

#### Scenario: Monitored at threshold visible

- **WHEN** a guest-menu article is stock-monitored and `in_stock` equals the configured hide-below threshold
- **THEN** it MUST appear in the guest catalog

### Requirement: Soft gate when Pi is offline too long

The system MUST compare the event’s paired server appliance edge last-seen time to the event’s configured offline threshold (default 10 minutes when unset). When the threshold is exceeded, the guest surface MUST show a soft unavailable message and MUST block starting or completing guest payment until last-seen is fresh again. Browsing the menu MAY remain available.

#### Scenario: Offline beyond threshold

- **WHEN** the paired Pi last-seen age exceeds the configured offline minutes
- **THEN** the guest UI MUST show a soft message and MUST NOT allow payment

#### Scenario: Pi returns

- **WHEN** edge activity refreshes last-seen within the threshold
- **THEN** guest payment MUST be allowed again without manual admin action

### Requirement: Guest surface hosted on order subdomain

The guest ordering UI MUST be served from `order.vendiqo.ch` (or the environment-equivalent order host), not from the admin host. Table QR links MUST target that guest host.

#### Scenario: QR targets order host

- **WHEN** a table QR for guest self-order is generated
- **THEN** its encoded URL MUST use the guest order host

### Requirement: Waiter ordering remains available

Enabling guest self-order MUST NOT disable waiter table ordering on the Pi. Waiter orders on the same table MUST continue to follow the event’s existing payment mode and settlement rules. Paid guest orders MUST NOT be included in waiter open-tab settlement, split-pay, or collective-bill assignment.

#### Scenario: Parallel waiter order

- **WHEN** guest self-order is active and a waiter submits a table order for the same table number
- **THEN** the waiter order MUST be created under existing Pi waiter semantics

#### Scenario: Guest lines excluded from settle

- **WHEN** staff settle an open table that also has paid guest orders
- **THEN** settlement MUST apply only to unsettled waiter (or other non-guest-prepaid) lines
