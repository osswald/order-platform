## ADDED Requirements

### Requirement: Edit dialog can add appliances to a rental

The rental edit surface SHALL allow a tenant admin to assign additional available appliances to the rental being edited (membership add). Create-rental from the calendar MUST remain without a device picker (empty rental first). Adding a device MUST use the same assign and overlap rules as other assign paths. Unassign planned and return current behaviour remains unchanged.

#### Scenario: Add device from edit dialog

- **WHEN** a tenant admin opens edit for a rental
- **AND** chooses an available appliance to add
- **THEN** an open lending for that appliance is created on the rental
- **AND** the device list updates without closing the dialog unless the product chooses to

#### Scenario: Add blocked by interior overlap

- **WHEN** the chosen appliance has an open lending that strictly overlaps the rental dates
- **THEN** the add is rejected
- **AND** the dialog shows an error
- **AND** no new lending is created

#### Scenario: Create dialog stays empty of devices

- **WHEN** a tenant admin opens create rental from the calendar
- **THEN** the create surface does not offer an appliance multi-picker
- **AND** the rental can still be created with zero devices

## MODIFIED Requirements

### Requirement: Edit dialog manages assigned devices and delete when allowed

The edit surface SHALL list the rental’s appliance lendings and allow adding an available appliance, removing a planned lending, or returning a current lending without deleting the rental. It SHALL offer delete/cancel when the rental may be deleted under existing rules (empty, or planned-only with no current open lending). Delete MUST be unavailable or rejected when a current open lending exists. Lending dates are not independently editable; only membership changes.

#### Scenario: Unassign planned device

- **WHEN** a tenant admin removes a planned device from the edit dialog
- **THEN** that lending is deleted
- **AND** the rental remains
- **AND** the device list updates

#### Scenario: Return current device

- **WHEN** a tenant admin returns a current device from the edit dialog
- **THEN** that lending is marked returned
- **AND** the rental remains

#### Scenario: Add available device

- **WHEN** a tenant admin adds an available appliance from the edit dialog
- **THEN** that appliance appears in the rental’s lending list as an open lending

#### Scenario: Delete empty or planned-only rental

- **WHEN** a tenant admin deletes a rental that has no current open lending and is empty or planned-only
- **THEN** the rental is removed
- **AND** the dialog closes
- **AND** the calendar no longer shows that rental

#### Scenario: Delete blocked while current lending exists

- **WHEN** a rental has a current open lending
- **THEN** delete is not offered or is rejected
- **AND** the rental remains until the current lending is returned
