## ADDED Requirements

### Requirement: Pending submissions are pushed before restore application

When a sync cycle performs a restore check that receives a **200** operational snapshot and will call operational restore, the Pi SHALL push pending (and retryable error) **submission** outbox rows to cloud using the cycle’s shared HTTP client **before** applying `restore_operational_snapshot` for that cycle. Bundle pull and restore-check gating (including idle debounce and snapshot **304** skip) MAY remain as today; this requirement only orders push ahead of restore application when restore will run.

#### Scenario: New open order pushed before ghost cleanup in same cycle

- **WHEN** a sync cycle has at least one pending submission outbox row for a newly created local open order
- **AND** a restore check runs and the operational snapshot returns 200 such that restore will apply
- **THEN** the Pi SHALL attempt to push those submission outbox rows before ghost cleanup runs in that restore
- **AND** a failure to push MUST NOT by itself delete the local open order when pending/error outbox protection in `pi-operational-restore` still applies

#### Scenario: Snapshot 304 still skips restore

- **WHEN** a restore check receives 304 for the operational snapshot
- **THEN** the Pi MUST NOT apply operational restore
- **AND** outbox push MAY still run later in the cycle as today
