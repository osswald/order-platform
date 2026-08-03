## Purpose

Make cloud admin reporting for busy events and organisation dashboards scale by aggregating edge order mirrors in the database while preserving operator-facing report meaning and response compatibility.

## ADDED Requirements

### Requirement: Event statistics filter and aggregate in the database

Event statistics endpoints MUST apply the requested time range and compute aggregate metrics using database queries over normalized edge order item data, not by loading every order item for the event into application memory and filtering in Python.

#### Scenario: Stats for a time window on a large event

- **WHEN** an operator requests event statistics for an event with a large volume of order items and a bounded start/end window
- **THEN** the response includes the same categories of aggregates as today (totals, breakdowns the UI already consumes)
- **AND** the server does not materialize the full event’s order-item set in process memory solely to discard rows outside the window

#### Scenario: Empty window

- **WHEN** the requested time range contains no order items
- **THEN** the API returns a valid empty/zeroed stats payload consistent with current empty behavior
- **AND** does not error

### Requirement: Organisation dashboard summaries avoid per-event full sales scans

Organisation dashboard summary generation MUST NOT build a full per-event sales report for every production event when only summary totals are required. Summary metrics MUST be derived from set-oriented queries (or equivalent pre-aggregated sources) scoped to the organisation’s relevant events.

#### Scenario: Dashboard with multiple production events

- **WHEN** an organisation has multiple events in production with substantial order history
- **THEN** the dashboard summary endpoint returns the summary fields the admin UI already displays
- **AND** the server does not invoke a full sales-report builder once per production event as the means to obtain those summaries

### Requirement: Sales and related report aggregates prefer SQL over full payload scans

Sales summary and related admin report builders that today scan all submitted orders or order items for an event MUST compute core totals and line aggregations via SQL against edge mirror tables when those tables contain the needed facts, preserving the JSON fields the cloud admin UI relies on.

#### Scenario: Sales report totals match prior meaning

- **WHEN** an event has mirrored order items and the operator opens the sales report
- **THEN** headline totals and primary breakdowns remain consistent with the previous report meaning for settled/relevant rows
- **AND** any intentional discrepancy is covered by tests documenting the chosen source of truth (normalized mirrors)

#### Scenario: Event with no orders

- **WHEN** an event has no submitted orders / order items
- **THEN** sales and stats endpoints return empty structures compatible with the UI
- **AND** respond successfully

### Requirement: Report routes do not load full event configuration graphs

HTTP handlers that only need event identity, organisation, and status for reporting MUST NOT eager-load the full event configuration relationship graph (stations, layouts, cells, waiters, vouchers, registers) as a prerequisite.

#### Scenario: Stats endpoint load path

- **WHEN** a client calls an event statistics or sales report route
- **THEN** authorization and event tenancy checks still apply
- **AND** the handler does not pay for a multi-collection configuration eager-load solely to read `event.id` / `organisation_id`

### Requirement: Transaction listing remains paginated without loading all orders for aggregates that can be windowed

Event transaction list endpoints that advertise pagination MUST NOT load the entire event order set into memory for the common sort/filter path when a SQL or windowed query can produce the page. If a specific filter still requires a fallback scan, that fallback MUST be limited to documented filter modes, not the default path.

#### Scenario: Default created-at page

- **WHEN** a client requests a transactions page with default sort by created time and no exotic kind filter
- **THEN** the response includes only the requested page of items plus pagination metadata
- **AND** the server does not load all event orders into memory to build that page

### Requirement: Hot reporting foreign keys are indexed

Columns used as the primary filter for busy-event reporting queries (at minimum submitted-order `event_id`, and organisation scoping used by those queries) MUST be indexed in PostgreSQL so range and aggregate plans do not require sequential scans of the full table as volume grows.

#### Scenario: Explain-friendly event_id filter

- **WHEN** migrations for this change are applied
- **THEN** `EdgeSubmittedOrder.event_id` (and organisation scope columns used by the new aggregate queries, if not already indexed) have supporting indexes
- **AND** existing unique constraints (e.g. client order id) remain intact
