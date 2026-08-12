## Purpose

Makes appliance-detail and organisation Geräte lending flows rental-aware so operators always attach devices through an explicit rental (pick existing or create new) and can see which rental each lending belongs to.

## ADDED Requirements

### Requirement: Appliance lend requires choosing or creating a rental

When a tenant admin lends an appliance from the appliance detail surface, the system SHALL require selecting an existing rental for the target organisation or creating a new rental (dates and optional label), then assigning the appliance to that rental. The flow MUST NOT silently create a rental without presenting that choice. On success the UI SHALL show a toast and remain on the appliance page.

#### Scenario: Assign to an existing rental

- **WHEN** a tenant admin chooses an existing rental for the organisation and confirms lend
- **THEN** the appliance is assigned to that rental
- **AND** a success toast is shown
- **AND** the user stays on the appliance detail view

#### Scenario: Create rental then assign

- **WHEN** a tenant admin chooses create-new, provides a valid date range and optional label, and confirms
- **THEN** a rental is created for that organisation
- **AND** the appliance is assigned to it
- **AND** a success toast is shown

#### Scenario: Conflicting existing rental cannot be used

- **WHEN** the selected rental’s dates strictly overlap an open lending of the appliance
- **THEN** the lend is rejected or the rental is not selectable
- **AND** no new lending is created

### Requirement: Appliance lending history is grouped by rental

The appliance lending history/detail SHALL group lendings under foldable sections keyed by rental. Sections MUST be ordered newest rental first (by rental start date descending). Each section header MUST show the rental display name. Expanding and collapsing sections MUST not remove return/cancel actions on individual lendings.

#### Scenario: History shows foldable rental groups newest first

- **WHEN** an appliance has lendings on two rentals with different start dates
- **AND** the user opens lending history
- **THEN** lendings appear under two foldable rental headers
- **AND** the rental with the later start date appears first

#### Scenario: Actions remain available inside a group

- **WHEN** a group contains a current open lending
- **THEN** the user can still return that lending from within the group

### Requirement: Organisation Geräte tab is rental-aware

On the organisation Geräte (appliance lendings) tab, the system SHALL keep a device-centric list that includes **current**, **planned**, and **past** sections. Each row MUST show the rental display name for that lending. Tenant admins MUST lend via the same pick-existing-or-create-new rental choice, then select one or more appliances to assign. Cancelling a planned lending MUST remain available. Organisation members MUST NOT gain rental create/assign permissions from this tab.

#### Scenario: Past lendings are listed

- **WHEN** an organisation has past appliance lendings
- **AND** a user opens the organisation Geräte tab
- **THEN** past lendings are visible in a past section
- **AND** each row shows the rental display name

#### Scenario: Lend appliances via rental choice

- **WHEN** a tenant admin opens lend appliances on the organisation tab
- **AND** picks an existing rental or creates a new one
- **AND** selects one or more available appliances
- **THEN** those appliances are assigned to that rental
- **AND** a success toast is shown

#### Scenario: Org member cannot create rentals from the tab

- **WHEN** an organisation member views the Geräte tab
- **THEN** they can see lending lists including past
- **AND** they cannot open a lend/create-rental action
