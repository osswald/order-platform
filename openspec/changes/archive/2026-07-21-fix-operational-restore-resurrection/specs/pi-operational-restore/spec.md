## ADDED Requirements

### Requirement: Local completed kitchen tickets survive restore

When restoring operational state for an order that already has one or more local kitchen tickets and every local ticket for that order has `status = done`, the Pi SHALL NOT delete, replace, or regenerate kitchen tickets for that order.

#### Scenario: Done local tickets with empty cloud kitchen

- **WHEN** a local order has kitchen tickets all with `status = done`
- **AND** the cloud operational snapshot includes that order as open with no kitchen tickets (or an empty tickets list)
- **AND** operational restore runs for the event
- **THEN** the local done kitchen tickets SHALL remain unchanged
- **AND** the kitchen monitor list for that printer SHALL continue to omit that order

#### Scenario: Done local tickets with stale open cloud kitchen

- **WHEN** a local order has kitchen tickets all with `status = done`
- **AND** the cloud snapshot includes open or partial kitchen tickets for that order
- **AND** operational restore runs
- **THEN** the Pi SHALL keep the local done tickets and SHALL NOT apply the cloud kitchen tickets for that order

### Requirement: Restore does not invent kitchen tickets from order lines

When the cloud operational snapshot provides no kitchen tickets for an open order, restore SHALL NOT create new kitchen tickets by regrouping the order’s lines onto kitchen-monitor printers.

#### Scenario: Open cloud order without kitchen snapshot

- **WHEN** restore processes a cloud open order with an empty or missing kitchen tickets entry
- **AND** the local order has no kitchen tickets (including empty-Pi takeover)
- **THEN** the Pi SHALL leave the order without kitchen tickets
- **AND** SHALL NOT create `open` tickets from order lines

#### Scenario: Cloud kitchen tickets still restore on empty local

- **WHEN** restore processes a cloud open order that includes non-empty kitchen tickets
- **AND** the local order has no all-done kitchen tickets blocking restore
- **THEN** the Pi SHALL recreate kitchen tickets from the cloud payload (including `status` and `qty_printed`)

### Requirement: Locally paid orders are not reopened by restore

When a local order exists with `payment_status = paid` for a given `client_order_id`, operational restore SHALL NOT overwrite that order from a cloud open-order payload and SHALL NOT restore kitchen tickets for that order in the same cycle.

#### Scenario: Paid local order vs open cloud mirror

- **WHEN** a local order is `paid`
- **AND** the cloud snapshot still lists the same `client_order_id` under open orders
- **AND** operational restore runs
- **THEN** the local order SHALL remain `paid` with its existing payload
- **AND** kitchen tickets for that order SHALL not be rewritten by restore

### Requirement: Locally progressed open orders are not clobbered by older cloud payloads

When a local order is still `open` but local settlement has progressed beyond the cloud open payload (pending/error outbox for that `client_order_id`, or fewer remaining sellable line quantities than the cloud payload), restore SHALL NOT overwrite that local order’s payload or payment fields from cloud.

#### Scenario: Pending settlement outbox protects local open order

- **WHEN** a local open order has a pending or error outbox submission for its `client_order_id`
- **AND** the cloud snapshot contains an older open payload for that id
- **AND** operational restore runs
- **THEN** the local order payload and `payment_status` SHALL remain unchanged by restore

#### Scenario: Partial settle fewer lines than cloud

- **WHEN** a local open order has fewer remaining sellable line quantities than the cloud open payload for the same `client_order_id`
- **AND** operational restore runs
- **THEN** the local reduced lines SHALL remain
- **AND** restore SHALL NOT expand the order back to the cloud line set

### Requirement: Genuine takeover restore still applies cloud open state

On a Pi with no conflicting local paid or all-done kitchen state for a `client_order_id`, restore SHALL continue to create or update the local open order from the cloud open payload and SHALL apply non-empty cloud kitchen tickets when present.

#### Scenario: Empty Pi restores open table with kitchen tickets

- **WHEN** no local order exists for a cloud open `client_order_id`
- **AND** the cloud snapshot includes kitchen tickets for that order
- **AND** operational restore runs
- **THEN** the Pi SHALL create the local open order from the cloud payload
- **AND** SHALL create kitchen tickets matching the cloud ticket statuses and printed quantities
