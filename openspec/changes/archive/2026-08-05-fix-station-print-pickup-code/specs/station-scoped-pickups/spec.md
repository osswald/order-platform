## MODIFIED Requirements

### Requirement: Station slips and kitchen tickets use the station pickup code

Each customer Abholbeleg and each kitchen ticket (or station kitchen print job) for a cash-register order SHALL display the pickup code allocated to that production station, not a shared order-wide code. When a station or kitchen PrintJob is created with a station-scoped `pickup_code`, that value MUST be stored in the job’s render payload used for ESC/POS (overriding any order-level scalar `pickup_code` on the parent order payload).

#### Scenario: Abholbelege differ by station

- **WHEN** a multi-station cash-register order is created
- **THEN** each customer pickup print job’s ESC/POS payload contains its station’s pickup code as the hero code

#### Scenario: Kitchen ticket shows station code

- **WHEN** a kitchen ticket is listed or printed for a station on a multi-station register order
- **THEN** the ticket’s pickup code is the code allocated to that station

#### Scenario: Direct station print uses station code

- **WHEN** a cash-register order creates a direct `station_order` PrintJob for a production station (no kitchen-monitor ticket for that group)
- **THEN** that job’s render payload / ESC/POS output contains that station’s pickup code as the hero code

#### Scenario: Kitchen monitor print uses station code not first order code

- **WHEN** a multi-station cash-register order has distinct pickup codes per station
- **AND** an operator prints a kitchen ticket for a station whose code is not the order’s first (`pickup_code`) scalar
- **THEN** the resulting `kitchen_ticket` PrintJob’s render payload / ESC/POS output contains that station’s pickup code
- **AND** it MUST NOT use the order-level first pickup code as the slip hero
