## ADDED Requirements

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

## MODIFIED Requirements

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
