# kitchen-monitor-order-chrome Specification

## Purpose

Kitchen monitors show how many tickets are still open in the header title, and each Bestellungen ticket shows whether it is table service or pickup without using wait-time colors or growing the ticket.

## Requirements

### Requirement: Open-ticket count in the kitchen title row

The kitchen monitor header title row SHALL show the station label together with the number of currently loaded open kitchen tickets for that station, in German, including when the count is zero. The count SHALL update as the open-ticket list changes. The same header (and therefore the same count) SHALL remain visible when the Produkte view is active.

#### Scenario: Count appears next to the station label

- **WHEN** the kitchen monitor is shown for a station that has open tickets
- **THEN** the title row SHALL include the station label and the open-ticket count in the form `{station} · {n} offen`

#### Scenario: Zero count when the board is empty

- **WHEN** the kitchen monitor is shown and there are no open tickets for that station
- **THEN** the title row SHALL include `0 offen`

#### Scenario: Count remains visible on Produkte

- **WHEN** the operator switches from Bestellungen to Produkte
- **THEN** the title row SHALL still show the open-ticket count for that station

### Requirement: Table vs pickup icon on each Bestellungen ticket

Each open-order ticket in Bestellungen view SHALL show a type icon at the top right of the ticket’s existing title line. Pickup tickets (those with a pickup code) SHALL use a takeout-box icon. All other tickets SHALL use a table-and-chair icon. Location text already on the ticket (`Tisch …` / `Pickup …`) MUST remain. The icon MUST sit in the existing title line and MUST NOT add a header row, extra ticket padding, or a change to column gap or column-width math.

#### Scenario: Table ticket shows table icon top right

- **WHEN** a Bestellungen ticket has no pickup code
- **THEN** the ticket SHALL show a table-and-chair type icon at the top right of the title line
- **AND** the title text SHALL still identify the table

#### Scenario: Pickup ticket shows takeout icon top right

- **WHEN** a Bestellungen ticket has a pickup code
- **THEN** the ticket SHALL show a takeout-box type icon at the top right of the title line
- **AND** the title text SHALL still identify the pickup code

#### Scenario: Ticket outer size and gaps unchanged

- **WHEN** Bestellungen tickets render with type icons
- **THEN** ticket header padding, ticket outer size, column gap, and minimum column width SHALL match the existing kitchen layout contract

### Requirement: Type icon colors stay distinct from wait time

Table and pickup type icons SHALL use cool glyph colors that are not green, amber, or red. Wait-time urgency MUST remain expressed only by the existing top bar. Type icons MUST NOT use a second colored bar or filled chip that could be read as urgency. Elapsed-time text MUST NOT take the type-icon color.

#### Scenario: Table uses sky, pickup uses violet

- **WHEN** a table ticket is shown
- **THEN** its type icon SHALL be sky `#38bdf8`
- **WHEN** a pickup ticket is shown
- **THEN** its type icon SHALL be violet `#c084fc`

#### Scenario: Wait-time bar colors unchanged

- **WHEN** a ticket’s wait time crosses the existing green / amber / red thresholds
- **THEN** only the existing top urgency bar SHALL use `#22c55e`, `#f59e0b`, or `#ef4444` for that signal
- **AND** the type icon SHALL keep its sky or violet color
