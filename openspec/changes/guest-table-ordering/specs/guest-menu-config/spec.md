## Purpose

Define cloud admin configuration for guest self-order at table: feature enablement, guest menu categories built from station articles, configurable thresholds, and table QR preview/print with the table number in the center.

## ADDED Requirements

### Requirement: Event-level guest self-order switch

The system MUST allow enabling or disabling guest self-order per event. The feature MUST default to disabled. When disabled, the guest ordering surface MUST NOT accept new orders for that event and the Pi MUST NOT run the guest-order poller for that event.

#### Scenario: Disabled by default

- **WHEN** a new event is created without explicitly enabling guest self-order
- **THEN** guest self-order MUST be disabled

#### Scenario: Enable shows guest menu config

- **WHEN** an admin enables guest self-order on an event
- **THEN** the event configuration UI MUST expose the Guest menu section

### Requirement: Guest menu categories from station articles

The Guest menu configuration MUST allow admins to create, rename, reorder, and delete menu categories. Admins MUST be able to add articles to a category only from articles assigned to the event’s stations. Staff app layouts MUST remain a separate configuration and MUST NOT be replaced by the guest menu.

#### Scenario: Add article from station

- **WHEN** an admin adds an article that is on an event station to a guest menu category
- **THEN** the article MUST be included in the guest catalog under that category

#### Scenario: Article not on any station rejected

- **WHEN** an admin attempts to add an article that is not on any event station to the guest menu
- **THEN** the system MUST reject the change

#### Scenario: Staff layouts unchanged

- **WHEN** the guest menu is configured
- **THEN** existing staff app layouts MUST continue to function unchanged for waiter and register UIs

### Requirement: Configurable stock hide threshold

The event guest self-order settings MUST include a configurable stock hide-below threshold used by the guest catalog. The default MUST be 15.

#### Scenario: Custom threshold persisted

- **WHEN** an admin sets the hide-below stock threshold to a positive integer and saves
- **THEN** subsequent guest catalog evaluations MUST use that value

### Requirement: Configurable Pi offline threshold

The event guest self-order settings MUST include a configurable Pi offline duration in minutes used by the guest soft gate. The default MUST be 10.

#### Scenario: Custom offline minutes persisted

- **WHEN** an admin sets the Pi offline threshold minutes and saves
- **THEN** the guest soft gate MUST use that duration

### Requirement: Table QR with centered table number

The system MUST generate table QR codes whose payload opens the guest order host for that event and table, including a token that authorizes ordering for that table. The QR artwork MUST display the table number in the center of the code in a human-readable form.

#### Scenario: Centered number

- **WHEN** a table QR is rendered for table 12
- **THEN** the visual MUST include a readable “12” (or equivalent table label) in the center region of the QR

#### Scenario: Payload binds event and table

- **WHEN** a guest scans a valid table QR
- **THEN** the guest surface MUST open for that event with that table number bound for subsequent orders

### Requirement: Print table QRs from Guest menu tab

The Guest menu section MUST allow generating a printable sheet (or equivalent print/PDF output) of table QR codes for a selected table number range.

#### Scenario: Print range

- **WHEN** an admin requests print for tables 1 through 20 from the Guest menu section
- **THEN** the system MUST produce a printable output containing one QR per table in that range with centered table numbers
