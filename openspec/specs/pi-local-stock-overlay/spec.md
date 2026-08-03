# pi-local-stock-overlay Specification

## Purpose
Keeps monitored article and ingredient stock on the Pi in a durable overlay so order and reapply paths update sellable state without rewriting the full organisation catalogue blob on SD card.
## Requirements
### Requirement: Stock mutations do not rewrite the catalogue blob

When the Pi applies local monitored stock changes for an order (or an equivalent stock-only update), it MUST persist those stock field changes without rewriting the durable organisation catalogue JSON body that holds event configuration and receipt artwork. Subsequent reads in the same process MUST observe the updated `in_stock` / `sellable` state for affected articles and ingredients.

#### Scenario: Order stock persists without catalogue rewrite

- **WHEN** an order path successfully deducts monitored stock
- **THEN** the durable organisation catalogue JSON body MUST remain unchanged by that stock persist
- **AND** a later bundle read in the same process MUST show the reduced stock / sellable state

#### Scenario: Restart still sees local stock

- **WHEN** local stock was persisted via the overlay path
- **AND** the Pi process restarts with the same durable store
- **THEN** bundle reads MUST show the same local stock overrides merged onto the stored catalogue baseline

### Requirement: Fresh catalogue baseline clears and rebuilds local stock overrides

When the Pi persists a new organisation catalogue body from cloud (or an equivalent full catalogue restore that replaces the baseline), it MUST clear prior local stock overrides for that appliance store and MUST rebuild local stock state by re-applying deductions from still-unacked outbox work onto that new baseline (when any such work exists). When no pending/error outbox stock applies, effective stock MUST match the new catalogue baseline.

#### Scenario: Changed pull with pending outbox

- **WHEN** a sync pull persists a changed organisation catalogue body
- **AND** at least one pending or error outbox row still carries order lines that affect monitored stock
- **THEN** effective stock MUST equal that new baseline after those pending deductions
- **AND** those effective stock values MUST be durably available after restart

#### Scenario: Changed pull with empty outbox

- **WHEN** a sync pull persists a changed organisation catalogue body
- **AND** there is no pending or error outbox stock to apply
- **THEN** effective stock MUST match the new catalogue baseline (no stale local overrides)

### Requirement: Edge-visible bundle shape stays compatible

Public bundle helpers used by edge routes MUST continue to return an organisation dict whose event article/ingredient stock fields reflect the effective (catalogue ⊕ local) state. Callers MUST NOT need a separate stock API to see correct sellable state.

#### Scenario: Strict helper reflects overlay

- **WHEN** local stock overrides exist for an event article
- **AND** a caller uses the strict organisation bundle helper
- **THEN** that article’s `in_stock` / `sellable` in the returned event MUST match the override
