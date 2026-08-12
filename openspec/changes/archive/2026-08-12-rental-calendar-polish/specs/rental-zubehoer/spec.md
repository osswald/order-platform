## ADDED Requirements

### Requirement: Catalog add may override quantity

When a tenant admin adds a Zubehör line from the catalog, the system SHALL allow an optional quantity override. If omitted, the catalog item’s default quantity MUST be used (including null when the catalog has no default). The UI SHOULD prefill the override field from the catalog default when selecting an item.

#### Scenario: Quantity override on catalog add

- **WHEN** a tenant admin adds catalog item "Thermopapier" (default quantity 2) with quantity 7
- **THEN** the rental Zubehör line is stored with quantity 7
- **AND** the label remains the catalog snapshot name

#### Scenario: Omitted override uses catalog default

- **WHEN** a tenant admin adds the same catalog item without a quantity override
- **THEN** the line quantity equals the catalog default quantity (2)
