## ADDED Requirements

### Requirement: Transaction history tolerates malformed order lines

The cloud transaction-history API SHALL return a successful page when a persisted order payload contains a malformed line. A line that lacks a usable `article_id` or contains values that cannot be processed by the existing pricing rules MUST be excluded from rendered line details, line count, and computed line total.

#### Scenario: Line without article id

- **WHEN** an event transaction contains an order line with no `article_id`
- **THEN** `GET /events/{event_id}/transactions` returns HTTP 200
- **AND** the malformed line is absent from `lines` and `line_count`
- **AND** it contributes zero to `line_cents`

#### Scenario: Invalid numeric article id

- **WHEN** an event transaction contains an order line whose `article_id` cannot be converted to an integer
- **THEN** the transaction endpoint returns HTTP 200 and excludes that line

### Requirement: Valid transaction data is preserved

When an order contains both valid and malformed lines, the cloud transaction-history API MUST retain all valid lines and calculate line details, count, and total from those valid lines. Order-level and payment information MUST remain available even when all order lines are malformed.

#### Scenario: Mixed valid and malformed lines

- **WHEN** a transaction contains one valid priced line and one malformed line
- **THEN** the response includes the valid line
- **AND** `line_count` and `line_cents` reflect only that valid line

#### Scenario: Payment remains visible

- **WHEN** every order line is malformed but the order contains a valid payment entry
- **THEN** the transaction remains in the response
- **AND** `paid_cents` and `payment_methods` reflect the payment
- **AND** `lines` is empty and `line_cents` is zero

### Requirement: One malformed transaction does not hide the event page

A malformed order line in one transaction MUST NOT prevent other transactions on the same page from being returned.

#### Scenario: Malformed order alongside valid order

- **WHEN** an event transaction page contains a malformed order and a valid order
- **THEN** the endpoint returns HTTP 200 with both transaction rows
- **AND** the valid order is rendered without modification
