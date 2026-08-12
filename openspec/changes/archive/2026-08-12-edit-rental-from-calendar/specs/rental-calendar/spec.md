## ADDED Requirements

### Requirement: Clicking a rental bar opens edit on month and year views

On the rentals calendar month and year views, clicking an existing rental bar MUST open an edit surface for that rental. The click MUST NOT create a new rental. Clicking empty day cells (month) or empty year-track areas MUST continue to open create. Fleet view click behaviour MUST remain unchanged in this change.

#### Scenario: Month bar opens edit

- **WHEN** a tenant admin clicks a rental bar on the month view
- **THEN** an edit dialog for that rental opens
- **AND** no new rental is created

#### Scenario: Year bar opens edit

- **WHEN** a tenant admin clicks a rental bar on the year view
- **THEN** an edit dialog for that rental opens
- **AND** no new rental is created

#### Scenario: Empty day still creates

- **WHEN** a tenant admin clicks an empty area of a month day cell (not on a rental bar)
- **THEN** the create rental dialog opens for that day

### Requirement: Edit dialog updates label and dates and shows organisation read-only

The edit surface SHALL allow changing the rental label and inclusive start/end dates. The organisation MUST be shown and MUST NOT be editable. Saving dates MUST use the existing rental date-update rules (open lendings move with the rental; overlap rejects the whole update). Display name rules (label or organisation name) remain unchanged.

#### Scenario: Save label and dates

- **WHEN** a tenant admin changes the label and/or dates and saves
- **THEN** the rental is updated
- **AND** month/year views refresh to show the new display name and span

#### Scenario: Organisation is not editable

- **WHEN** the edit dialog is open
- **THEN** the organisation is visible
- **AND** the user cannot change which organisation the rental belongs to

#### Scenario: Overlapping date change is rejected

- **WHEN** saving new dates would overlap an open lending of an assigned appliance on another rental
- **THEN** the system rejects the save
- **AND** the dialog remains open with an error
- **AND** the rental keeps its previous dates until a successful save

### Requirement: Edit dialog manages assigned devices and delete when allowed

The edit surface SHALL list the rental’s appliance lendings and allow removing a planned lending or returning a current lending without deleting the rental. It SHALL offer delete/cancel when the rental may be deleted under existing rules (empty, or planned-only with no current open lending). Delete MUST be unavailable or rejected when a current open lending exists.

#### Scenario: Unassign planned device

- **WHEN** a tenant admin removes a planned device from the edit dialog
- **THEN** that lending is deleted
- **AND** the rental remains
- **AND** the device list updates

#### Scenario: Return current device

- **WHEN** a tenant admin returns a current device from the edit dialog
- **THEN** that lending is marked returned
- **AND** the rental remains

#### Scenario: Delete empty or planned-only rental

- **WHEN** a tenant admin deletes a rental that has no current open lending and is empty or planned-only
- **THEN** the rental is removed
- **AND** the dialog closes
- **AND** the calendar no longer shows that rental

#### Scenario: Delete blocked while current lending exists

- **WHEN** a rental has a current open lending
- **THEN** delete is not offered or is rejected
- **AND** the rental remains until the current lending is returned
