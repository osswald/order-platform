## MODIFIED Requirements

### Requirement: Ingest keeps queryable membership fields current

On edge submitted-order create/update paths that carry order payloads, the system MUST keep the queryable collective-bill membership fields aligned with `payload.collective_bill_uuid` (and any companion fields required for close/list filters, such as payment status if denormalized). Existing rows MUST be backfilled so historical busy events benefit without re-sync.

The Alembic backfill that populates denormalized `collective_bill_uuid` from `payload` on PostgreSQL MUST use SQL operators that are valid for the column’s Postgres type (`json`). It MUST NOT rely on jsonb-only operators (for example `?`) against a `json` payload column.

#### Scenario: New collective order sync

- **WHEN** the edge submits an order payload that includes `collective_bill_uuid`
- **THEN** subsequent collective-bill list queries for that event can find the order via the SQL membership filter
- **AND** the bill header upsert behavior continues to run as today

#### Scenario: Backfill after migration

- **WHEN** the migration/backfill for this change has been applied
- **THEN** previously stored orders whose payload contains `collective_bill_uuid` are discoverable by the new SQL filters
- **AND** orders without that payload key remain excluded from collective membership queries

#### Scenario: Postgres json payload backfill is upgrade-safe

- **WHEN** Alembic upgrades through the collective-bill UUID backfill revision on PostgreSQL where `edge_submitted_orders.payload` is type `json`
- **THEN** the upgrade completes successfully without `operator does not exist` errors for jsonb-only operators
- **AND** `alembic_version` advances to that revision
