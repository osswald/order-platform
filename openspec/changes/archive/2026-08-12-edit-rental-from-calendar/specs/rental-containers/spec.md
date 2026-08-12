## ADDED Requirements

### Requirement: Organisation is immutable after rental create

Once a rental is created, the system MUST NOT allow changing its `organisation_id`. Updates MAY change label and/or dates (subject to existing overlap and date rules). Clients that need a different organisation MUST create a new rental.

#### Scenario: Update rejects organisation change

- **WHEN** a client attempts to change a rental’s organisation after create
- **THEN** the system does not change the organisation
- **AND** either the request has no organisation field (PATCH label/dates only) or an explicit organisation change is rejected

#### Scenario: Label and dates remain updatable

- **WHEN** a tenant admin updates only the label and/or dates of an existing rental
- **THEN** the update succeeds when date rules are satisfied
- **AND** the organisation stays the same
