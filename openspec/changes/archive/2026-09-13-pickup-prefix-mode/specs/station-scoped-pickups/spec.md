## MODIFIED Requirements

### Requirement: Per-station pickup codes on cash-register orders

When creating a cash-register order, the system SHALL allocate one sequential pickup number per production-station group that contains article lines. The letter prefix and number series SHALL follow the event’s `pickup_prefix_mode`:

- **`register`:** use the cash register’s `pickup_code_prefix` and the event-wide pickup counter (burning N numbers for N groups), as today.
- **`station`:** use that group’s station `pickup_code_prefix` and that station’s per-station pickup counter. Article lines that do not resolve to a production station SHALL cause order creation to fail.

The create response SHALL include `pickup_codes` (all allocated codes in allocation order) and MAY include `pickup_code` as the first code. A single-station order SHALL allocate exactly one code.

#### Scenario: Multi-station order gets distinct codes

- **WHEN** `pickup_prefix_mode` is `register`
- **AND** a cash-register order contains article lines for two production stations
- **THEN** the system allocates two pickup codes with the register prefix and consecutive numbers from the event-wide counter
- **AND** `pickup_codes` contains both codes
- **AND** `pickup_code` equals the first allocated code

#### Scenario: Single-station order unchanged

- **WHEN** a cash-register order contains article lines for only one production station
- **THEN** the system allocates exactly one pickup code
- **AND** that code is used for the customer Abholbeleg and any kitchen ticket for that station

#### Scenario: Multi-station order uses station letters

- **WHEN** `pickup_prefix_mode` is `station`
- **AND** a cash-register order contains article lines for stations with prefixes `G` and `B`
- **THEN** the system allocates one code with prefix `G` and one with prefix `B`
- **AND** each code’s number comes from that station’s own counter
- **AND** `pickup_codes` contains both codes

#### Scenario: Null station rejected in station mode

- **WHEN** `pickup_prefix_mode` is `station`
- **AND** a cash-register order has an article line that does not resolve to a production station
- **THEN** order creation fails
- **AND** no pickup codes are committed for that order
