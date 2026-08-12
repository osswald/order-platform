# rental-containers Specification

## Purpose

Gives each Verleiher a dated rental container for an organisation so hardware can be committed, assigned, or left empty without tying that booking to POS events.

## Requirements

### Requirement: Rental is a tenant-scoped dated container

The system SHALL persist a rental as a container belonging to one hire company (tenant) and one organisation of that tenant, with an inclusive UTC calendar `start_date` and `end_date` (`end_date` on or after `start_date`). A rental MAY have an optional label. A rental MUST be valid with zero appliance lendings.

#### Scenario: Empty rental can be created

- **WHEN** a tenant admin creates a rental for an organisation in their Verleiher with a valid date range and no appliances
- **THEN** the rental is stored and listed for that tenant
- **AND** it has no appliance lendings

#### Scenario: Label is optional

- **WHEN** a tenant admin creates a rental without a label
- **THEN** the rental is stored with a null/empty label
- **AND** its display name is the organisation name

#### Scenario: Labelled rental uses the label as display name

- **WHEN** a rental has a non-empty label
- **THEN** the display name is that label
- **AND** the organisation name is not copied into the label field

#### Scenario: Organisation must belong to the tenant

- **WHEN** a tenant admin attempts to create a rental for an organisation that is not in the active Verleiher
- **THEN** the system rejects the request
- **AND** no rental is created

#### Scenario: Invalid date range is rejected

- **WHEN** a create or update sets `end_date` before `start_date`
- **THEN** the system rejects the request

### Requirement: Every appliance lending belongs to a rental

The system SHALL require every appliance lending to reference exactly one rental. The lending’s organisation MUST match the rental’s organisation. The lending’s `start_date` and `end_date` MUST equal the rental’s dates when the lending is created or when the rental dates are updated (except a returned lending keeps its historical dates). A lending MUST NOT exist without a rental. Overlap for assignment uses the handover-day rule (endpoint-touch allowed; interior overlap rejected).

#### Scenario: Assigning a device creates a lending on the rental

- **WHEN** a tenant admin assigns an available appliance to a rental
- **THEN** an open appliance lending is created for that appliance, the rental’s organisation, and the rental’s date range

#### Scenario: Overlap still blocks assignment

- **WHEN** an appliance already has an open lending that strictly overlaps the rental’s date range (shares more than a single endpoint day)
- **THEN** assigning that appliance to the rental is rejected
- **AND** no new lending is created

#### Scenario: Floating lending cannot be created

- **WHEN** a client attempts to create an appliance lending that is not attached to a rental
- **THEN** the system rejects the request

#### Scenario: Assigned device inherits rental window

- **WHEN** a rental spans 12–15 June and a device is assigned
- **THEN** the lending start is 12 June and the lending end is 15 June

#### Scenario: Endpoint-touch does not count as overlap

- **WHEN** an appliance has an open lending ending on day D
- **AND** a tenant admin assigns it to a rental starting on day D
- **THEN** the assignment is accepted

### Requirement: Open lendings may touch on a handover day

Open appliance lendings for the same appliance MUST be allowed to share an endpoint calendar day: an open lending with `end_date` D MUST NOT block assigning the same appliance to another rental whose `start_date` is D. Assignment MUST still be rejected when the open date ranges share any day other than a single shared endpoint (strict overlap). Returned lendings MUST NOT participate in overlap checks. The same overlap rule MUST apply to rental date moves and appliance lend-availability checks.

#### Scenario: Handover day assignment succeeds

- **WHEN** an appliance has an open lending ending 15 June
- **AND** a tenant admin assigns that appliance to another rental that starts 15 June
- **THEN** the assignment succeeds
- **AND** both lendings remain open

#### Scenario: Interior overlap is still rejected

- **WHEN** an appliance has an open lending ending 15 June
- **AND** a tenant admin assigns that appliance to a rental that starts 14 June and ends after 15 June
- **THEN** the assignment is rejected
- **AND** no new lending is created

#### Scenario: Returned lending does not block the return day

- **WHEN** an appliance lending is marked returned on calendar day D
- **AND** a tenant admin assigns that appliance to a rental whose date range includes D
- **THEN** the assignment succeeds

#### Scenario: Identical one-day windows may both be open

- **WHEN** an appliance has an open lending with start and end on 15 June
- **AND** a tenant admin assigns that appliance to another rental that also starts and ends on 15 June
- **THEN** the assignment succeeds under the handover rule

### Requirement: Active lending on a shared day prefers the arriving rental

When more than one open lending for the same appliance covers a given UTC calendar day, the system SHALL treat the lending whose `start_date` equals that day as the active lending for that day (edge/POS org context and appliance “lent today” status). If several open lendings start on that day, the system SHALL pick a stable deterministic winner (lowest lending id). Fleet occupancy MAY still show every open lending that covers the day.

#### Scenario: Edge uses the rental that starts today

- **WHEN** appliance P has open lending A ending today and open lending B starting today
- **AND** the edge device for P authenticates for today’s org context
- **THEN** the organisation from lending B is used
- **AND** the request is not rejected for lack of an active lending

### Requirement: Lending reads expose rental identity

Appliance and organisation lending list/detail payloads SHALL include the lending’s `rental_id` and the rental display name (label if set, otherwise organisation name) so clients can group and label by rental.

#### Scenario: Organisation lending item includes rental fields

- **WHEN** a client lists appliance lendings for an organisation
- **THEN** each item includes `rental_id` and `rental_display_name`

#### Scenario: Appliance lending history includes rental fields

- **WHEN** a client reads an appliance with lending history
- **THEN** each lending entry includes `rental_id` and `rental_display_name`

### Requirement: Rental dates move assigned open lendings

When a tenant admin changes a rental’s start or end date, the system SHALL update every open (not returned) appliance lending on that rental to the new dates. The change MUST be rejected if any of those lendings would overlap another open lending for the same appliance. Returned lendings MUST NOT be rewritten.

#### Scenario: Date change updates all open devices

- **WHEN** a rental with two open lendings is extended by one day
- **THEN** both lendings’ end dates become the new rental end date

#### Scenario: Date change that would overlap is rejected

- **WHEN** moving a rental’s dates would overlap an open lending of one assigned appliance on another rental
- **THEN** the update is rejected
- **AND** the rental and all lendings keep their previous dates

### Requirement: Unassign, return, and cancel do not require deleting the rental

The system SHALL allow removing a planned lending from a rental and returning a current lending without deleting the rental. An empty rental MUST remain until explicitly deleted or cancelled. A rental with a current (started, not returned) lending MUST NOT be deleted.

#### Scenario: Remove planned device leaves the rental

- **WHEN** a tenant admin removes a planned appliance from a rental
- **THEN** that lending is deleted
- **AND** the rental still exists

#### Scenario: Return current device leaves the rental

- **WHEN** a tenant admin returns a current appliance lending
- **THEN** that lending is marked returned
- **AND** the rental still exists with its original dates

#### Scenario: Empty rental can be deleted

- **WHEN** a tenant admin deletes a rental that has no appliance lendings
- **THEN** the rental is removed

#### Scenario: Rental with only planned lendings can be cancelled

- **WHEN** a tenant admin cancels a rental whose lendings are all planned (start after today) or already returned
- **THEN** planned lendings are deleted
- **AND** the rental is removed

#### Scenario: Rental with a current lending cannot be deleted

- **WHEN** a tenant admin attempts to delete a rental that has a current open lending
- **THEN** the system rejects the request
- **AND** the rental and lendings remain

### Requirement: Rentals are isolated per tenant

List, read, update, assign, and delete operations on rentals SHALL be scoped to the active Verleiher. Organisation members and organisation admins MUST NOT create, update, or delete rentals. Platform admins MUST operate only on the active hire company.

#### Scenario: Tenant admin lists only their Verleiher’s rentals

- **WHEN** a tenant admin lists rentals
- **THEN** the response includes only rentals whose hire company is the active Verleiher

#### Scenario: Organisation user cannot create a rental

- **WHEN** an organisation admin or member attempts to create a rental
- **THEN** the system rejects the request as forbidden

#### Scenario: Cross-tenant rental is not readable

- **WHEN** a tenant admin requests a rental id that belongs to another Verleiher
- **THEN** the system responds with not found or forbidden
- **AND** no rental data from the other tenant is returned

### Requirement: Legacy lendings are backfilled into rentals

On migration, every existing appliance lending SHALL be attached to a rental with the same organisation and date range and a null label. After migration, no lending row MAY have a null rental reference.

#### Scenario: Existing lending becomes a one-device rental

- **WHEN** the migration runs against a lending for organisation O from date A to date B
- **THEN** a rental exists for O with dates A–B and no label
- **AND** that lending references that rental

### Requirement: Events stay independent of rentals

The system MUST NOT require a rental to have an event, MUST NOT require an event to have a rental, and MUST NOT persist a foreign key between rentals and events in this change.

#### Scenario: Rental exists without events

- **WHEN** an organisation has no events
- **AND** a tenant admin creates a rental for that organisation
- **THEN** the rental is stored successfully

#### Scenario: Event exists without a rental

- **WHEN** an organisation has an event and no rentals
- **THEN** event create, update, and POS configuration continue to work without a rental

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
