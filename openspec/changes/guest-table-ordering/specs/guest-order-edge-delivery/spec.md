## Purpose

Define how the Pi pulls paid guest orders from cloud when guest self-order is active, applies them as local paid table-routed orders, deducts stock on apply, drives kitchen/print, and acknowledges delivery.

## ADDED Requirements

### Requirement: Feature-gated separate guest-order poller

The Pi MUST poll cloud for pending paid guest orders on a dedicated poll path separate from the catalogue/bundle sync cycle. The poller MUST run only when at least one paired event has guest self-order enabled. When no such event is active, the Pi MUST NOT call the guest-order pull endpoint.

#### Scenario: Poller idle when feature off

- **WHEN** no paired event has guest self-order enabled
- **THEN** the Pi MUST NOT perform guest-order pull requests

#### Scenario: Poller active when feature on

- **WHEN** a paired event has guest self-order enabled
- **THEN** the Pi MUST periodically pull pending paid guest orders for that event on the dedicated poll path

### Requirement: Apply paid guest order locally after pull

When the Pi pulls a pending paid guest order, it MUST create a local paid order that includes the guest’s lines and table number, and MUST route kitchen tickets and/or station print jobs using existing table/station routing rules. The local order MUST be marked as originating from guest self-order so settlement tools can exclude it from open-tab flows.

#### Scenario: Kitchen receives table-routed guest order

- **WHEN** the Pi successfully applies a paid guest order for table N with station-routed lines
- **THEN** kitchen and/or print fulfillment MUST be created for those lines with table N

#### Scenario: Born paid

- **WHEN** a pulled guest order is applied
- **THEN** the local order MUST have paid payment status and MUST NOT require waiter settlement to reach the kitchen

### Requirement: Stock deducted on Pi apply

The Pi MUST deduct monitored stock when applying a pulled guest order using the same local stock deduction path as other local orders. Cloud MUST NOT deduct stock for that guest order solely because payment succeeded.

#### Scenario: Deduct on apply

- **WHEN** the Pi applies a pulled guest order containing monitored articles
- **THEN** local monitored stock for those articles MUST decrease accordingly

### Requirement: Idempotent ack after apply

After successful local apply, the Pi MUST acknowledge the guest order to cloud so it leaves the pending-pull inbox. Re-pulling or re-acking the same guest order id MUST NOT create duplicate local orders or duplicate kitchen/print work.

#### Scenario: Ack removes from inbox

- **WHEN** the Pi acks a successfully applied guest order
- **THEN** subsequent pulls MUST NOT return that order as pending

#### Scenario: Duplicate pull is safe

- **WHEN** the Pi pulls or applies the same guest order id more than once
- **THEN** at most one local order and one fulfillment set MUST exist for that id

### Requirement: Edge poll refreshes liveness

Guest-order pull (or ack) requests authenticated as the edge appliance MUST update the edge credential last-seen timestamp used by the guest soft gate.

#### Scenario: Poll updates last-seen

- **WHEN** the Pi successfully authenticates a guest-order pull request
- **THEN** cloud MUST refresh last-seen for that edge credential
