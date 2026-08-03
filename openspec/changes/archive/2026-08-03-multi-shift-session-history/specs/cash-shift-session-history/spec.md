## ADDED Requirements

### Requirement: Shift identity is a UUID minted at open

When shift settlement opens a cash session for a waiter or cash register, the Pi SHALL assign a new `cash_session_uuid` that is unique for that session instance and SHALL persist it for the life of the session. The system SHALL NOT reuse that UUID for a later open of the same subject on the same event.

#### Scenario: Waiter opens a shift

- **WHEN** a waiter opens a shift on an event with shift settlement enabled
- **THEN** the created session SHALL have a non-empty `cash_session_uuid`
- **AND** sync payloads for that session SHALL include the same `cash_session_uuid`

#### Scenario: Register opens a shift

- **WHEN** a cash register opens a shift on an event with shift settlement enabled
- **THEN** the created session SHALL have a non-empty `cash_session_uuid`
- **AND** sync payloads for that session SHALL include the same `cash_session_uuid`

### Requirement: At most one open shift per subject per event

The Pi SHALL refuse to open a second shift for the same waiter or the same cash register on the same event while an OPEN session already exists for that subject. After the open session is CLOSED, the Pi SHALL allow opening a new session with a new `cash_session_uuid`.

#### Scenario: Second open while still open is rejected

- **WHEN** a waiter already has an OPEN shift on an event
- **AND** a client attempts to open another waiter shift for the same waiter and event
- **THEN** the Pi SHALL reject the open (conflict)
- **AND** no new session row SHALL be created

#### Scenario: Sequential shifts after close

- **WHEN** a waiter’s shift on an event is CLOSED
- **AND** the same waiter opens a new shift on the same event
- **THEN** the Pi SHALL create a new session with a different `cash_session_uuid`
- **AND** both session rows SHALL remain available locally

### Requirement: Cloud retains every synced shift instance

Cloud cash-session ingest SHALL upsert by organisation, event, and `cash_session_uuid`. The system SHALL NOT use `subject_key` alone as the uniqueness key for storing shift history. Re-sync of the same `cash_session_uuid` SHALL update that row in place (including status and ledger payload).

#### Scenario: Two closed waiter shifts both stored

- **WHEN** the same waiter closes shift A then opens and closes shift B on one event
- **AND** both sessions sync to cloud with distinct `cash_session_uuid` values
- **THEN** cloud SHALL store two `EdgeCashSession` rows for that event and waiter subject
- **AND** neither row SHALL overwrite the other

#### Scenario: Re-sync updates same instance

- **WHEN** an OPEN session with a given `cash_session_uuid` is already stored in cloud
- **AND** a later chunk for the same `cash_session_uuid` reports CLOSED with final wallet and ledger
- **THEN** cloud SHALL update the existing row to CLOSED with the new payload
- **AND** SHALL NOT create a second row for that UUID

### Requirement: Admin list shows all shifts for the event

The event cash-sessions (Schichten) admin API and list SHALL return every stored shift for the event, including multiple rows for the same waiter or cash register, ordered according to the existing list sorting (default newest started first unless the client requests otherwise).

#### Scenario: Schichten list includes sequential shifts

- **WHEN** an event has two CLOSED cash sessions for the same waiter with different `cash_session_uuid` values
- **AND** an authorised user requests the event cash-sessions list
- **THEN** the response SHALL include both sessions
- **AND** each item SHALL be distinguishable by identity (id and/or `cash_session_uuid`) and start/end times

### Requirement: Open restore still selects by subject

Operational snapshot and restore SHALL continue to expose and apply only OPEN cash sessions, selecting at most one open session per subject (`waiter:{uuid}` or `cash_register:{uuid}`). Closed historical sessions SHALL remain in cloud storage and SHALL NOT be removed solely because a newer open or closed session exists for the same subject.

#### Scenario: Snapshot includes open only

- **WHEN** cloud holds one CLOSED and one OPEN cash session for the same waiter on an event
- **AND** an operational snapshot is built for that event
- **THEN** the snapshot’s open cash sessions SHALL include the OPEN session
- **AND** SHALL NOT include the CLOSED session as an open restore target

#### Scenario: Closed history survives newer shift

- **WHEN** a CLOSED session for a waiter exists in cloud
- **AND** a newer OPEN or CLOSED session for the same waiter syncs with a different `cash_session_uuid`
- **THEN** the earlier CLOSED row SHALL remain stored
