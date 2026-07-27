## ADDED Requirements

### Requirement: Per-station pickup codes on cash-register orders

When creating a cash-register order, the system SHALL allocate one sequential pickup number per production-station group that contains article lines, using the cash register’s `pickup_code_prefix` and the existing per-event pickup counter (burning N numbers for N groups). The create response SHALL include `pickup_codes` (all allocated codes in allocation order) and MAY include `pickup_code` as the first code. A single-station order SHALL allocate exactly one code.

#### Scenario: Multi-station order gets distinct codes

- **WHEN** a cash-register order contains article lines for two production stations
- **THEN** the system allocates two pickup codes with the register prefix and consecutive numbers
- **AND** `pickup_codes` contains both codes
- **AND** `pickup_code` equals the first allocated code

#### Scenario: Single-station order unchanged

- **WHEN** a cash-register order contains article lines for only one production station
- **THEN** the system allocates exactly one pickup code
- **AND** that code is used for the customer Abholbeleg and any kitchen ticket for that station

### Requirement: Station slips and kitchen tickets use the station pickup code

Each customer Abholbeleg and each kitchen ticket (or station kitchen print job) for a cash-register order SHALL display the pickup code allocated to that production station, not a shared order-wide code.

#### Scenario: Abholbelege differ by station

- **WHEN** a multi-station cash-register order is created
- **THEN** each customer pickup print job’s ESC/POS payload contains its station’s pickup code as the hero code

#### Scenario: Kitchen ticket shows station code

- **WHEN** a kitchen ticket is listed or printed for a station on a multi-station register order
- **THEN** the ticket’s pickup code is the code allocated to that station

### Requirement: Independent pickup readiness per station

Each station pickup SHALL move to `ready` when that station’s kitchen work is complete, without waiting for other stations on the same order. If a station group has no kitchen-monitor ticket (direct station print only), that station pickup SHALL be `ready` at order creation. Partial kitchen print SHALL leave the station pickup `pending` until the ticket is fully done.

#### Scenario: One station ready while another pending

- **WHEN** a multi-station register order has kitchen tickets for Grill and Bar
- **AND** only the Grill ticket reaches `done`
- **THEN** the Grill station pickup is `ready`
- **AND** the Bar station pickup remains `pending`

#### Scenario: Direct-print station ready immediately

- **WHEN** a register order station group creates a station print job but no kitchen ticket
- **THEN** that station pickup is `ready` at order creation

### Requirement: Pickup screen lists and clears station pickups independently

The pickup listing API SHALL return one entry per station pickup in `pending` or `ready` status (not one entry per order). Marking picked-up SHALL clear a single station pickup by its id. The ready TTL SHALL expire each `ready` station pickup independently after the existing TTL window.

#### Scenario: Two tiles for one order

- **WHEN** a multi-station register order has Grill `ready` and Bar `pending`
- **THEN** the pickup list includes two entries with those codes and statuses

#### Scenario: Picked-up one code at a time

- **WHEN** an operator marks the Grill station pickup as picked up
- **THEN** only the Grill entry leaves the pickup list
- **AND** the Bar entry remains until it is ready and picked up (or expired)

#### Scenario: Ready TTL per code

- **WHEN** a station pickup has been `ready` longer than the ready TTL
- **THEN** the system marks that station pickup picked up without affecting sibling station pickups on the same order

### Requirement: Register surfaces show all pickup codes on one order row

The register customer display and pay-success flows SHALL present all pickup codes for the order. The open-orders list SHALL remain one row per open register order and SHALL expose all pickup codes for that order (for display such as `A1, A2`).

#### Scenario: Display shows all codes

- **WHEN** a multi-station register order is created
- **THEN** the register display payload includes all allocated pickup codes

#### Scenario: Open-orders one row with all codes

- **WHEN** an open multi-station register order is listed for a register
- **THEN** the list contains a single row for that order
- **AND** the row includes all of the order’s pickup codes

### Requirement: Partial settlement keeps station pickups on the original order

When a register order is partially settled, all station pickups SHALL remain associated with the original open order (not the new paid order).

#### Scenario: Partial settle preserves pickups

- **WHEN** a subset of lines on a multi-station open register order is settled
- **THEN** the original order stays open with its station pickups unchanged
- **AND** the new paid order does not own those pickup codes
