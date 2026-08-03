## ADDED Requirements

### Requirement: Pending stock reapply runs only after a real catalogue baseline change

After a bundle pull, the Pi MUST re-apply stock deductions from pending/error outbox rows onto the organisation catalogue only when that pull persisted a changed catalogue baseline (`bundle_changed`). On HTTP 304 or identical-body skip, the Pi MUST NOT re-apply those deductions again and MUST NOT perform a stock durable write solely because of that pull.

#### Scenario: 304 with pending outbox does not re-decrement

- **WHEN** a sync pull receives 304 for the organisation bundle
- **AND** at least one outbox row is `pending` or `error` with order lines
- **AND** local effective stock already reflects those lines
- **THEN** effective monitored stock MUST remain unchanged by that pull’s post-processing
- **AND** the durable organisation catalogue JSON body MUST NOT be rewritten by pending-stock reapply for that pull

#### Scenario: Identical-body skip behaves like 304 for reapply

- **WHEN** a sync pull downloads a body identical to the stored catalogue baseline
- **AND** pending outbox stock exists
- **THEN** the Pi MUST NOT re-apply pending stock deductions for that pull

#### Scenario: Real body change still reapplies pending stock

- **WHEN** a sync pull persists a changed organisation catalogue body
- **AND** pending or error outbox rows carry monitored stock lines
- **THEN** the Pi MUST re-apply those deductions onto the new baseline so effective stock accounts for unacked local orders
