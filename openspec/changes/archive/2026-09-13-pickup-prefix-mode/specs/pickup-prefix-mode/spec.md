## Purpose

Event-level choice of whether pickup-code letters come from cash registers or production stations, including config validation, UI field visibility, mode locking, per-station numbering in station mode, and event copy.

## ADDED Requirements

### Requirement: Event pickup prefix mode

Each event SHALL have a `pickup_prefix_mode` of `register` (default) or `station`. In `register` mode, pickup-code letters SHALL come from each cash register’s `pickup_code_prefix`. In `station` mode, pickup-code letters SHALL come from each production station’s `pickup_code_prefix`.

#### Scenario: Default is register mode

- **WHEN** a new event is created without an explicit pickup prefix mode
- **THEN** `pickup_prefix_mode` is `register`

#### Scenario: Station mode uses station letters

- **WHEN** `pickup_prefix_mode` is `station`
- **AND** a cash-register order allocates a pickup code for a production station
- **THEN** the code’s letter prefix is that station’s `pickup_code_prefix`
- **AND** it is not taken from the cash register’s `pickup_code_prefix`

### Requirement: Config UI shows only active-mode prefix fields

The cloud event configuration UI SHALL show cash-register `pickup_code_prefix` fields only when mode is `register`, and station `pickup_code_prefix` fields only when mode is `station`.

#### Scenario: Register mode hides station prefixes

- **WHEN** the operator views event configuration with `pickup_prefix_mode` = `register`
- **THEN** cash-register prefix inputs are visible
- **AND** station prefix inputs are not shown

#### Scenario: Station mode hides register prefixes

- **WHEN** the operator views event configuration with `pickup_prefix_mode` = `station`
- **THEN** station prefix inputs are visible
- **AND** cash-register prefix inputs are not shown

### Requirement: Station prefixes required and unique in station mode

When `pickup_prefix_mode` is `station`, each production station SHALL have a `pickup_code_prefix` of 1–3 uppercase letters `A–Z`, and those prefixes SHALL be unique within the event. Saving configuration that violates this SHALL fail.

#### Scenario: Missing station prefix rejected

- **WHEN** mode is `station`
- **AND** the operator saves configuration with a station missing a valid prefix
- **THEN** the save is rejected

#### Scenario: Duplicate station prefixes rejected

- **WHEN** mode is `station`
- **AND** two stations would share the same normalized prefix
- **THEN** the save is rejected

### Requirement: Sellable articles require a station in station mode

When `pickup_prefix_mode` is `station`, every article that appears on an app layout for the event SHALL belong to at least one production station. Saving configuration that leaves a layout article off all stations SHALL fail.

#### Scenario: Layout article without station rejected

- **WHEN** mode is `station`
- **AND** an app-layout cell references an article not assigned to any station
- **THEN** the save is rejected

### Requirement: Mode change locked after config status

The system SHALL allow changing `pickup_prefix_mode` only while the event status is `config`. Attempts to change the mode when status is `test`, `prod`, or `archive` SHALL be rejected. The configuration UI SHALL disable the mode control outside `config`.

#### Scenario: Mode change allowed in config

- **WHEN** event status is `config`
- **AND** the operator changes `pickup_prefix_mode` and saves
- **THEN** the new mode is persisted

#### Scenario: Mode change rejected in prod

- **WHEN** event status is `prod`
- **AND** a client attempts to change `pickup_prefix_mode`
- **THEN** the update is rejected
- **AND** the stored mode is unchanged

### Requirement: Per-station pickup numbers in station mode

When `pickup_prefix_mode` is `station`, each production station SHALL have its own sequential pickup number series for that event. Allocating a code for station S SHALL advance only S’s counter. Register mode SHALL keep a single event-wide pickup number series.

#### Scenario: Independent station sequences

- **WHEN** mode is `station`
- **AND** Grill and Bar each receive a pickup allocation
- **THEN** Grill’s numbers form one sequence (e.g. G1, G2)
- **AND** Bar’s numbers form a separate sequence (e.g. B1, B2)

#### Scenario: Register mode keeps shared counter

- **WHEN** mode is `register`
- **AND** two allocations occur for the same event (any stations)
- **THEN** they share one event-wide number sequence as today

### Requirement: Event copy preserves mode and prefixes

Copying an event SHALL copy `pickup_prefix_mode`, each cash register’s `pickup_code_prefix`, and each station’s `pickup_code_prefix` onto the new event.

#### Scenario: Station-mode event copy

- **WHEN** an event with `pickup_prefix_mode` = `station` and station prefixes G and B is copied
- **THEN** the new event has `pickup_prefix_mode` = `station`
- **AND** the corresponding new stations have prefixes G and B

### Requirement: Pickup counters reset on test to prod

When an event transitions from `test` to `prod`, the system SHALL clear all pickup-code counters for that event (the event-wide series and every per-station series). The next cash-register pickup allocation after the transition SHALL start numbering from the beginning of each series again.

#### Scenario: Register-mode counter restarts after test to prod

- **WHEN** an event in `register` mode has already issued pickup numbers in `test`
- **AND** the event status changes from `test` to `prod`
- **THEN** the event-wide pickup counter for that event is cleared
- **AND** the next allocated pickup number for that event is `1`

#### Scenario: Station-mode counters restart after test to prod

- **WHEN** an event in `station` mode has already issued per-station pickup numbers in `test`
- **AND** the event status changes from `test` to `prod`
- **THEN** all per-station pickup counters for that event are cleared
- **AND** the next allocated number for each station starts at `1` again
