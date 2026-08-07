# pi-admin-load-test Specification

## Purpose

Lets ops run a guarded volume simulation on a Pi against a `test` event, placing concurrent waiter and register orders through the real create/settle path so printers, drawers, and monitors see realistic load before a live event.

## Requirements

### Requirement: Lasttest available only for test events
The system SHALL expose the Lasttest admin tool only when the selected event has status `test`, and SHALL reject starting a load-test job unless that event’s status is `test`.

#### Scenario: Tile hidden for non-test event
- **WHEN** an admin opens Betrieb for an event whose status is not `test`
- **THEN** the Lasttest entry is not available for that event

#### Scenario: Start rejected for non-test event
- **WHEN** a client requests to start a load-test job for an event whose status is not `test`
- **THEN** the system rejects the request without placing orders

#### Scenario: Running job aborts if status leaves test
- **WHEN** a load-test job is running and the event status is no longer `test`
- **THEN** the job stops placing further orders and ends in a failed or stopped state

### Requirement: Configurable volume simulation
The system SHALL accept load-test configuration of waiter count, cash register count, table number range, and total order count, capped by the waiters and cash registers present on the selected event.

#### Scenario: Counts capped by event inventory
- **WHEN** the requested waiter or cash register count exceeds the number available on the event
- **THEN** the system uses at most the available count (or rejects the start with a clear error)

#### Scenario: Progress reflects configuration
- **WHEN** a load-test job is started with valid configuration
- **THEN** status reporting includes the effective configuration and progress toward the total order count

### Requirement: Concurrent minute bursts
The system SHALL place orders in bursts of one order per configured waiter actor and one order per configured cash register actor, with actors in a burst posting concurrently, at most one burst per minute, until the configured total is reached or the job is stopped.

#### Scenario: Burst uses all configured actors
- **WHEN** a burst runs with W waiters and R registers and remaining orders ≥ W+R
- **THEN** the system attempts W waiter orders and R register orders in that burst concurrently

#### Scenario: Partial final burst
- **WHEN** remaining orders are fewer than the number of actors
- **THEN** the final burst places only the remaining orders

#### Scenario: Stop ends further bursts
- **WHEN** an admin stops a running load-test job
- **THEN** no further bursts are started after the stop is acknowledged

### Requirement: Realistic baskets from event catalogue
Each synthetic order SHALL represent 1–8 people ordering from the event’s sellable non-addition articles, drawn from 1..n randomly chosen stations that have such articles. When a chosen article has additions, the system SHALL sometimes attach 1..k of them, weighting selection toward additions marked `preselected`.

#### Scenario: Multi-person basket
- **WHEN** a synthetic order is generated
- **THEN** it contains lines for between 1 and 8 people using real article IDs from the event

#### Scenario: Station-scoped article pick
- **WHEN** a synthetic order is generated
- **THEN** its base articles come from a non-empty random subset of stations that have sellable non-addition articles

#### Scenario: Weighted additions
- **WHEN** a base article has additions and additions are attached
- **THEN** between 1 and the number of available additions are included, with preference for `preselected` additions

### Requirement: Create, settle, and probabilistic payment receipt
Each successful synthetic placement SHALL create an order through the normal edge create path, fully settle it with cash, and with approximately 30% probability enqueue a network payment-receipt print for that payment. Register cash settles SHALL kick the cash drawer as they would for any other register cash payment. Station, kitchen, and customer pickup print behavior SHALL match ordinary orders (kitchen tickets are not auto-printed by the load-test job).

#### Scenario: Waiter order settled
- **WHEN** a waiter actor places a synthetic order
- **THEN** the order is created with a table number in the configured range and settled with cash

#### Scenario: Register order settled with drawer
- **WHEN** a cash register actor places a synthetic order
- **THEN** the order is created as a cash-register order, settled with cash, and a cash-drawer kick is attempted as for a normal register cash settle

#### Scenario: Payment receipt sometimes printed
- **WHEN** many synthetic orders are settled
- **THEN** roughly 30% result in a network payment-receipt print request and the rest do not

### Requirement: Single-flight in-memory job with progress
The system SHALL allow at most one load-test job at a time on the Pi, keep job state in memory only, and expose start, status, and stop so the admin UI can show live progress.

#### Scenario: Second start rejected
- **WHEN** a load-test job is already running and a client tries to start another
- **THEN** the system rejects the second start

#### Scenario: Status while running
- **WHEN** a client polls status during a run
- **THEN** the response includes state, placed count, failed count, payment receipts printed, and burst progress

#### Scenario: Restart loses job state
- **WHEN** the Pi backend process restarts during or after a run
- **THEN** load-test job state is not restored (status returns to idle)
