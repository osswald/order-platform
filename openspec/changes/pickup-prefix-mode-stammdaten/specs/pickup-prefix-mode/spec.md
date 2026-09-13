## MODIFIED Requirements

### Requirement: Config UI shows only active-mode prefix fields

The cloud event configuration UI SHALL show cash-register `pickup_code_prefix` fields only when mode is `register`, and station `pickup_code_prefix` fields only when mode is `station`. The Stationen and Kassen sections SHALL NOT present a control to change `pickup_prefix_mode`.

#### Scenario: Register mode hides station prefixes

- **WHEN** the operator views event configuration with `pickup_prefix_mode` = `register`
- **THEN** cash-register prefix inputs are visible
- **AND** station prefix inputs are not shown

#### Scenario: Station mode hides register prefixes

- **WHEN** the operator views event configuration with `pickup_prefix_mode` = `station`
- **THEN** station prefix inputs are visible
- **AND** cash-register prefix inputs are not shown

#### Scenario: Mode control not on Stationen or Kassen

- **WHEN** the operator views the Stationen or Kassen configuration section
- **THEN** no **Abholcode-Buchstabe von** (pickup prefix mode) select is shown there

### Requirement: Mode change locked after config status

The system SHALL allow changing `pickup_prefix_mode` only while the event status is `config`. Attempts to change the mode when status is `test`, `prod`, or `archive` SHALL be rejected. The Stammdaten UI SHALL disable the mode control outside `config`.

#### Scenario: Mode change allowed in config

- **WHEN** event status is `config`
- **AND** the operator changes `pickup_prefix_mode` in Stammdaten and saves Stammdaten
- **THEN** the new mode is persisted

#### Scenario: Mode change rejected in prod

- **WHEN** event status is `prod`
- **AND** a client attempts to change `pickup_prefix_mode`
- **THEN** the update is rejected
- **AND** the stored mode is unchanged

#### Scenario: Mode control disabled outside config in Stammdaten

- **WHEN** event status is not `config`
- **AND** the operator views Stammdaten
- **THEN** the **Abholcode-Buchstabe von** control is disabled

## ADDED Requirements

### Requirement: Mode control lives in Stammdaten

The cloud event Stammdaten UI SHALL expose **Abholcode-Buchstabe von** (`pickup_prefix_mode`: register vs station). Changing the mode SHALL persist only when the operator saves Stammdaten (event update), not via configuration autosave.

#### Scenario: Station choice survives Stammdaten save and reload

- **WHEN** event status is `config`
- **AND** the operator sets **Abholcode-Buchstabe von** to Station in Stammdaten
- **AND** the operator saves Stammdaten
- **AND** the event is loaded again
- **THEN** `pickup_prefix_mode` is `station`
- **AND** the Stammdaten control shows Station

#### Scenario: Mode is not written by configuration autosave

- **WHEN** the operator edits stations or cash registers without saving Stammdaten
- **THEN** configuration autosave does not change the stored `pickup_prefix_mode`
