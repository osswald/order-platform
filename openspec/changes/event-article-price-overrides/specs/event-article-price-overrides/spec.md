## ADDED Requirements

### Requirement: Sparse event article price overrides

The system SHALL allow an event to optionally override the sell price of any catalogue article that belongs to that event’s Lager article set (station and layout articles plus linked additions). When no override exists for an article on an event, the organisation `Article.price` SHALL be used. Override rows MUST store price in the same major-unit Float representation as `Article.price`.

#### Scenario: Override replaces org price for one article

- **WHEN** an event has an override price for article A and no override for article B
- **THEN** the effective sell price for A on that event MUST be the override
- **AND** the effective sell price for B on that event MUST be B’s organisation `Article.price`

#### Scenario: Addition can have its own override

- **WHEN** a linked addition article is in the event’s Lager article set
- **AND** an override is stored for that addition article on the event
- **THEN** the effective sell price for that addition on the event MUST be the override

### Requirement: Clear override restores organisation price

Clearing an event price override for an article MUST remove the override so subsequent effective prices use the organisation `Article.price` again.

#### Scenario: Null or cleared override deletes the row

- **WHEN** an authorised client saves event stock/prices with a cleared or null event price for an article that previously had an override
- **THEN** the system MUST delete that article’s override for the event
- **AND** the effective sell price MUST equal the organisation `Article.price`

### Requirement: Lager tab shows org and event prices

The cloud event Lager tab SHALL list the same articles as today (including additions), show each article’s organisation price as read-only Stammpreis, and provide a separate Eventpreis input for the override. Overrides MUST be editable for the event regardless of event lifecycle status (subject to existing event edit authorisation).

#### Scenario: Operator sets and clears an override in Lager

- **WHEN** an operator enters a value in Eventpreis for an article and the Lager form saves successfully
- **THEN** that value MUST be stored as the event override for the article
- **WHEN** the operator clears Eventpreis and the form saves successfully
- **THEN** the override MUST be removed and Stammpreis MUST remain the organisation price

#### Scenario: Stammpreis reflects current article price

- **WHEN** the organisation `Article.price` changes while an event override exists
- **THEN** Stammpreis on the Lager tab MUST show the updated organisation price
- **AND** the override MUST remain until cleared

### Requirement: Edge bundle emits effective event prices

For each article (and nested addition) included in an event’s edge catalogue snapshot, the `price` field SHALL be the effective sell price for that event (`override` if present, otherwise `Article.price`). Pi and other edge consumers MUST continue to treat bundle `price` as the catalogue sell price for new sales.

#### Scenario: Bundle price uses override when present

- **WHEN** the organisation bundle is assembled for an event that has a price override for article A
- **THEN** `events[…].articles[A].price` MUST equal the override value
- **AND** nested addition entries for A (if any) MUST use A’s effective price consistently

#### Scenario: Bundle price falls back without override

- **WHEN** the organisation bundle is assembled for an event with no price override for article A
- **THEN** `events[…].articles[A].price` MUST equal A’s organisation `Article.price`

### Requirement: Event copy clones price overrides

Copying an event SHALL copy price overrides from the source event for every article id that remains in the new event’s allowed Lager article set after configuration is applied. Overrides for articles not in the new allowed set MUST NOT be copied.

#### Scenario: Overrides copy with event

- **WHEN** a source event has overrides for articles still assigned on the copied event
- **THEN** the new event MUST have the same override prices for those articles

#### Scenario: Orphan overrides are skipped

- **WHEN** a source event has an override for an article that is not in the new event’s allowed Lager set
- **THEN** that override MUST NOT be created on the new event
