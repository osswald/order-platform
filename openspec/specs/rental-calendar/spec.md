# rental-calendar Specification

## Purpose

Gives Verleiher admins a calendar of rental commitments and a fleet occupancy month so they can see who has kit when and which appliances are free, without exposing that planning surface to organisation users.

## Requirements

### Requirement: Calendar lives under Verwaltung for hire-company admins

The cloud admin SHALL expose a single Verwaltung navigation item labelled **Ausleihe** (German) / **Lending** (English) that opens the rental calendar/fleet surface. Access MUST use the same gate as appliances: `tenant_admin`, or `platform_admin` with an active Verleiher selected. Organisation admins and members MUST NOT see the item or load the route. The org-facing main-menu item **Geräteausleihen** MUST remain a separate label and route.

#### Scenario: Tenant admin sees the nav item

- **WHEN** a tenant admin opens the cloud admin with German locale
- **THEN** Verwaltung includes an item labelled Ausleihe
- **AND** they can open the calendar route

#### Scenario: English locale uses Lending

- **WHEN** a tenant admin opens the cloud admin with English locale
- **THEN** Administration includes an item labelled Lending

#### Scenario: Platform admin with active Verleiher can open the calendar

- **WHEN** a platform admin has selected an active hire company
- **THEN** they can open the calendar route
- **AND** it shows only that hire company’s rentals and appliances

#### Scenario: Platform admin without Verleiher cannot use the calendar

- **WHEN** a platform admin has no active hire company selected
- **THEN** the calendar is not available (hidden or redirected), same as appliances

#### Scenario: Organisation user cannot open the calendar

- **WHEN** an organisation admin or member requests the calendar route
- **THEN** they are denied
- **AND** the Verwaltung calendar item is not shown

### Requirement: Rentals calendar has month and year views

The calendar surface SHALL show all rentals of the active Verleiher in a month view and a year view. Each rental bar MUST use the rental display name (label if set, otherwise organisation name). Empty rentals MUST appear on these views, visually distinct from rentals that have at least one open (not returned) appliance lending.

#### Scenario: Month view shows rental spanning several days

- **WHEN** a rental for organisation “FC St.Gallen” runs 12–15 June and the user is on June month view
- **THEN** a bar labelled “FC St.Gallen” covers those days

#### Scenario: Labelled rental shows the label

- **WHEN** a rental has label “Openair 2026”
- **THEN** month and year views display “Openair 2026”

#### Scenario: Empty rental is visible on the rentals calendar

- **WHEN** a rental has no appliance lendings
- **AND** the user views a month or year that overlaps its dates
- **THEN** the rental is shown
- **AND** it is visually distinguishable from rentals that have assigned devices

#### Scenario: Year view shows rentals across months

- **WHEN** the user opens year view for a year that contains rentals
- **THEN** each overlapping rental is shown as a bar (or equivalent span) on that year

### Requirement: Fleet month view shows appliances by type and day

The same surface SHALL offer a month fleet view whose Y-axis lists the tenant’s non-hosted appliances grouped by type and whose X-axis is the calendar days of the selected month. A cell or bar MUST appear only where an appliance has an open lending that overlaps that day, labelled with the rental display name. Appliances with no lending that month MUST still appear as empty rows. Empty rentals MUST NOT occupy fleet cells.

#### Scenario: Assigned device occupies its days

- **WHEN** Pi-01 is assigned to a rental 12–15 June
- **AND** the user opens the June fleet view
- **THEN** Pi-01’s row is occupied on the 12th through 15th with that rental’s display name

#### Scenario: Type grouping

- **WHEN** the fleet includes servers and printers
- **THEN** those appliances are listed under type group headings (server, printer, and other types present)

#### Scenario: Unassigned appliance is an empty row

- **WHEN** an appliance has no open lending in the visible month
- **THEN** it still appears on the Y-axis with no occupancy bars

#### Scenario: Empty rental does not appear on the fleet

- **WHEN** a rental has no appliance lendings during the visible month
- **THEN** no fleet cell is occupied for that rental

### Requirement: Hire-company users can create a rental from the calendar

From the rentals calendar, an authorized user SHALL be able to create a rental by choosing an organisation, date range, and optional label, with appliances optional at create time. From the fleet view, assigning a free appliance on a day range SHALL either add it to an existing overlapping rental for the chosen organisation or create a rental and assign that appliance.

#### Scenario: Create empty rental from month view

- **WHEN** a tenant admin creates a rental from the calendar with organisation and dates and no devices
- **THEN** the new rental appears on the rentals calendar
- **AND** the fleet view is unchanged

#### Scenario: Assign free device from fleet view into a new rental

- **WHEN** a tenant admin assigns a free appliance on a date range from the fleet view and provides an organisation
- **THEN** a rental exists for that organisation and range
- **AND** that appliance occupies those days on the fleet view

### Requirement: Organisation-facing lending lists stay separate

The existing organisation-scoped appliance-lendings page in the main menu SHALL remain available to users who can select an organisation. It MUST NOT be replaced by the Verwaltung calendar in this change. Organisation users MUST still be unable to create rentals or lendings from that page.

#### Scenario: Org member still sees their lending list

- **WHEN** an organisation member with an active organisation opens Geräte-Ausleihen
- **THEN** they see current, planned, and past lendings for that organisation
- **AND** they do not see other organisations’ rentals or the fleet grid
