## Purpose

Ensure cloud admin collective-bill (Sammelrechnung) listing, close detection, and single-bill detail/PDF load only the submitted orders that belong to the relevant bills, scaling with busy events that have many non-collective orders.

## Requirements

### Requirement: Collective-bill order membership is queryable without scanning all event orders

The system MUST be able to select `EdgeSubmittedOrder` rows for an event that belong to a collective bill (and, when needed, a specific bill UUID) using database filters, without loading every submitted order for that event into application memory solely to read `payload.collective_bill_uuid`.

#### Scenario: List bills on an event with mixed order types

- **WHEN** an event has both collective-bill orders and many orders without a collective bill UUID
- **AND** an operator requests the collective-bills list for that event
- **THEN** the response includes the same bill UUIDs, statuses, and order membership meaning as today for collective orders
- **AND** the server does not materialize the full event submitted-order set in process memory only to discard non-collective rows

#### Scenario: Event with no collective bills

- **WHEN** an event has submitted orders but none carry a collective bill UUID
- **AND** the operator requests the collective-bills list
- **THEN** the API returns a valid empty (or header-only) collective-bills payload consistent with current empty behavior
- **AND** responds successfully without requiring a full payload scan of every order

### Requirement: Close detection queries only the bill’s orders

When determining whether a collective bill can be marked closed after an edge upsert, the server MUST evaluate open/paid state using only submitted orders associated with that bill UUID for the event, not every order on the event.

#### Scenario: Closing a bill while other event orders remain open

- **WHEN** all orders for bill UUID `B` are paid
- **AND** other non-bill (or other-bill) orders on the same event remain open
- **THEN** bill `B` may still be closed per existing close rules
- **AND** close detection does not load unrelated event orders solely to make that decision

### Requirement: Single-bill detail and PDF load one bill’s orders

Handlers that return or render a single collective bill MUST NOT rebuild the full multi-bill list as the only means to obtain that bill. They MUST load header + orders scoped to the requested bill UUID.

#### Scenario: PDF for one bill on a busy event

- **WHEN** an operator downloads the PDF for one collective bill on an event with many other bills and non-collective orders
- **THEN** the PDF content for that bill remains consistent with today’s single-bill meaning
- **AND** the server does not assemble every collective bill for the event solely to select one

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

### Requirement: Admin API response compatibility

Collective-bills list and single-bill/PDF inputs MUST preserve the JSON fields the cloud admin UI and PDF builder already consume (bill uuid, name, status, cents totals, line groups, orders, currency/country as applicable). Additive fields are allowed; removals are not.

#### Scenario: Existing list consumer

- **WHEN** the cloud admin collective-bills tab loads an event that already has bills in fixtures/tests
- **THEN** required keys such as `collective_bills`, per-bill `uuid` / `status` / `line_cents` / `orders` remain present with compatible types
- **AND** existing collective-bill tests continue to pass without UI contract changes
