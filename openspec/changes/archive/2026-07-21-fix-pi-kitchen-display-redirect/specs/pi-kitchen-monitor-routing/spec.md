## ADDED Requirements

### Requirement: Kitchen monitor URLs include event context

The Pi frontend SHALL include the target event id in kitchen monitor URLs generated for staff (copy and open), so the URL alone identifies which event the monitor should show.

#### Scenario: Admin copy kitchen URL includes event

- **WHEN** an admin copies a kitchen monitor URL for a printer slug while an operations event is selected
- **THEN** the copied URL SHALL include that event id as the `event` query parameter
- **AND** the path SHALL still be `/kitchen/:printerSlug` (optional view segment unchanged)

#### Scenario: Admin open kitchen monitor uses event URL

- **WHEN** an admin opens a kitchen monitor from Operations
- **THEN** the opened URL SHALL include the selected operations event id as the `event` query parameter

### Requirement: Cold navigation to kitchen monitor restores event

When the edge bundle is ready, navigating to a kitchen monitor URL that includes a valid `event` query parameter SHALL show the kitchen monitor for that event even if no waiter or register session exists and `selectedEventId` was previously unset.

#### Scenario: New tab kitchen URL with valid event

- **WHEN** the user navigates to `/kitchen/:printerSlug?event=<id>` (or with optional view segment)
- **AND** the bundle is ready and contains that event id
- **AND** no waiter/register session is present
- **THEN** the router SHALL allow the `kitchen` route
- **AND** the selected event SHALL be that event id

#### Scenario: Kitchen URL missing event redirects to events

- **WHEN** the user navigates to `/kitchen/:printerSlug` without an `event` query parameter
- **AND** `selectedEventId` is null
- **THEN** the router SHALL redirect to the Events page

#### Scenario: Kitchen URL with unknown event redirects to events

- **WHEN** the user navigates to `/kitchen/:printerSlug?event=<id>`
- **AND** the bundle is ready but does not contain that event id
- **AND** `selectedEventId` is null
- **THEN** the router SHALL redirect to the Events page

### Requirement: Event restore does not create operator sessions

Restoring `selectedEventId` from a display URL MUST NOT create or modify waiter or register session storage.

#### Scenario: Kitchen restore leaves sessions untouched

- **WHEN** a kitchen URL with a valid `event` query restores the selected event
- **THEN** waiter and register session keys SHALL remain unchanged
