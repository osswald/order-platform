## ADDED Requirements

### Requirement: Month bars span continuous day ranges within each week

On month view, each rental MUST render as continuous bar segment(s) across the days it occupies within a week row, not as one discrete chip per day. Multi-week rentals MAY produce one segment per week row they cross.

#### Scenario: Multi-day rental is week-spanning bars

- **WHEN** a rental runs Friday through Monday and the user is on that month view
- **THEN** the rental appears as continuous bars on the affected week rows
- **AND** it is not shown as one separate chip for each calendar day

### Requirement: Overlapping year rentals use separate lanes

On year view, when two or more rentals overlap in time within a month track, the calendar SHALL place them on separate vertical lanes so bars remain distinguishable.

#### Scenario: Concurrent year rentals stack

- **WHEN** two rentals overlap on the same year-view month track
- **THEN** they appear on different lanes
- **AND** both remain clickable for edit

### Requirement: Calendar bars expose rental summary tooltips

Month and year rental bars SHALL provide a tooltip (or equivalent hover/focus summary) that includes organisation name, inclusive date range, and the names of open appliances on that rental (from the list payload). Empty-device rentals MUST still show organisation and dates.

#### Scenario: Month bar tooltip lists devices

- **WHEN** a rental has open appliance lendings
- **AND** the user opens the tooltip on its month bar
- **THEN** the summary includes organisation, dates, and those appliance names

### Requirement: Assign and edit device lists show appliance type chips

In the rental edit/assign surfaces, assigned appliances and the add-device picker SHALL show the appliance type chip (icon and localized type label) beside the appliance name.

#### Scenario: Type chip visible when adding a device

- **WHEN** a tenant admin opens the add-device control on rental edit
- **THEN** each available appliance option shows its type chip with the appliance name

### Requirement: Devices view shows printer IP addresses

The calendar’s Geräte (devices/fleet) month view, rental edit device list, and bar tooltips SHALL include an appliance IP address when one is known (e.g. printers). Missing IPs MUST NOT block rendering the row or bar.

#### Scenario: Fleet row shows printer IP

- **WHEN** a printer appliance has an IP address configured
- **AND** the user opens the Geräte month view
- **THEN** that appliance’s row shows the IP address

### Requirement: Deleting a rental keeps the calendar surface visible

After a successful rental delete from the edit dialog, the UI SHALL show a success message and MUST keep the month/year/Geräte calendar views available (reloaded without the deleted rental). Delete MUST NOT replace the entire calendar with only the toast message.

#### Scenario: Calendar remains after delete

- **WHEN** a tenant admin deletes an empty or planned-only rental
- **THEN** a success message is shown
- **AND** the calendar grid for the current view remains visible without that rental

## MODIFIED Requirements

### Requirement: Fleet month view shows appliances by type and day

The same surface SHALL offer a month Geräte (devices) view — formerly referred to as fleet — whose Y-axis lists the tenant’s non-hosted appliances grouped by type (stable order: server, router, ap, printer, mobile, tablet, then any others) and whose X-axis is the calendar days of the selected month. A cell or bar MUST appear only where an appliance has an open lending that overlaps that day, labelled with the rental display name. Appliances with no lending that month MUST still appear as empty rows. Empty rentals MUST NOT occupy Geräte cells. Appliance rows SHOULD show IP when available.

#### Scenario: Assigned device occupies its days

- **WHEN** Pi-01 is assigned to a rental 12–15 June
- **AND** the user opens the June Geräte view
- **THEN** Pi-01’s row is occupied on the 12th through 15th with that rental’s display name

#### Scenario: Type grouping

- **WHEN** the Geräte view includes servers and printers
- **THEN** those appliances are listed under type group headings (server, printer, and other types present)

#### Scenario: Empty appliance still listed

- **WHEN** an appliance has no open lending in the selected month
- **THEN** it still appears as an empty row in its type group

#### Scenario: Empty rental does not appear on the Geräte view

- **WHEN** a rental has no open appliance lendings
- **THEN** no Geräte cell is occupied for that rental
