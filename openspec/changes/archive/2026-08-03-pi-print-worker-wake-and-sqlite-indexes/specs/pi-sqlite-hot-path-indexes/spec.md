## Purpose

Adds durable SQLite indexes on Pi hot-path filters so print polling, open-order lists, outbox sync, and kitchen queries avoid full-table scans as event data grows.

## ADDED Requirements

### Requirement: Print queue lookups use a status index

The Pi database schema SHALL include an index that supports filtering `print_jobs` by `status` (at minimum covering the worker’s `queued` scan). Migrated appliances MUST receive this index via Alembic; fresh `create_all` schemas MUST not omit an equivalent index.

#### Scenario: Queued jobs query is index-backed after upgrade

- **WHEN** Alembic has been upgraded to the revision that adds hot-path indexes
- **THEN** querying `print_jobs` filtered by `status = queued` MUST be able to use an index on `status` (alone or as the leading column of a composite)

### Requirement: Open-order and outbox filters are indexed

The Pi database schema SHALL include indexes supporting the common filters used for open local orders and pending/error sync outbox rows: at least `order_submissions` by `event_id` and `payment_status` (composite or equivalent), and `sync_outbox` by `status` (and optionally with `event_id`).

#### Scenario: Open orders by event and payment_status

- **WHEN** the hot-path index revision is applied
- **THEN** listing open orders for an event filtered by `payment_status` MUST be supported by an index whose leading columns match that filter pattern

#### Scenario: Outbox pending/error scan

- **WHEN** the hot-path index revision is applied
- **THEN** selecting `sync_outbox` rows by `status` in (`pending`, `error`) MUST be supported by an index on `status` (alone or leading)

### Requirement: Kitchen ticket status filters are indexed

The Pi database schema SHALL include an index supporting kitchen ticket queries that filter by `status` together with event or printer scope (for example `(event_id, status)` or `status` plus existing scoped indexes), so monitor and restore paths do not full-scan tickets as volume grows.

#### Scenario: Kitchen open tickets by event

- **WHEN** the hot-path index revision is applied
- **THEN** filtering `kitchen_tickets` by `event_id` and non-done `status` MUST be able to use an index that includes those columns in a usable order

### Requirement: ORM and Alembic stay aligned for these indexes

Indexes introduced for this capability MUST be reflected in SQLAlchemy models (or `__table_args__`) so in-memory test databases created via `create_all` expose the same index names/columns as migrated production schemas for the columns listed above.

#### Scenario: Test schema includes print_jobs status index

- **WHEN** tests initialise schema via the project’s `create_all` / `init_test_schema` path
- **THEN** an index supporting `print_jobs.status` MUST exist without requiring a separate Alembic upgrade step in that test DB
