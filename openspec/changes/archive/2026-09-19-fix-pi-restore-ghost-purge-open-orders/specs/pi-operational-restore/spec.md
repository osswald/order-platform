## ADDED Requirements

### Requirement: Ghost cleanup retains unsynced local open orders

When operational restore runs ghost cleanup for an event, the Pi SHALL NOT delete a local order with `payment_status = open` whose `client_order_id` has at least one sync outbox row in `pending` or `error` status for that event — even when that `client_order_id` is absent from the cloud snapshot’s open-order list. Ghost cleanup MAY still delete open local orders that have no such outbox protection and are not retained for another restore keep reason (for example present in the cloud open-order keep-set).

#### Scenario: New register order survives restore before cloud mirror

- **WHEN** a cash-register or waiter order is created locally as `open` and a pending outbox submission exists for its `client_order_id`
- **AND** the cloud operational snapshot for the event does not list that `client_order_id` under open orders
- **AND** operational restore runs ghost cleanup for the event
- **THEN** the local open order SHALL remain
- **AND** any kitchen tickets created for that order SHALL remain
- **AND** `GET /v1/orders/{id}/summary` for that order SHALL still succeed while it remains open
- **AND** `GET /v1/kitchen/orders` for the ticket’s kitchen-monitor printer SHALL still include that ticket while its status is not `done`

#### Scenario: New table order survives restore before cloud mirror

- **WHEN** a waiter table order is created locally as `open` with a pending outbox submission for its `client_order_id`
- **AND** the cloud snapshot does not list that id under open orders
- **AND** operational restore runs ghost cleanup
- **THEN** the local open order SHALL remain payable for that table (settle / transfer / assign still find an open submission)

#### Scenario: True ghost without outbox may still be purged

- **WHEN** a local open order has no pending or error outbox row for its `client_order_id`
- **AND** that id is not in the restore keep-set derived from the cloud open-order list (and other existing keep rules)
- **AND** operational restore runs ghost cleanup
- **THEN** the Pi MAY delete that local open order as a ghost

### Requirement: Ghost cleanup removes dependent order items

When ghost cleanup deletes a local open submission, the Pi SHALL also delete `order_items` rows that reference that submission (in addition to existing cleanup of kitchen tickets, station pickups, and matching outbox rows for that `client_order_id`).

#### Scenario: Purged submission leaves no OPEN items

- **WHEN** ghost cleanup deletes an open local submission that had normalized `order_items`
- **THEN** those `order_items` rows SHALL no longer exist
- **AND** no `order_items` row with `status = OPEN` SHALL remain pointing at the deleted submission id
