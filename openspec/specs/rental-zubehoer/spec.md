# rental-zubehoer Specification

## Purpose

Lets each Verleiher maintain a reusable Zubehör catalog and attach optional Zubehör lines to individual rentals for packing lists, without tying extras to POS articles or auto-adding them on rental create.

## Requirements

### Requirement: Tenant-scoped Zubehör catalog

The system SHALL provide a hire-company (tenant) catalog of Zubehör items. Each catalog item MUST have a non-empty name and MAY have an optional default quantity. Catalog CRUD MUST be restricted to tenant admins (and platform admins with an active Verleiher). Organisation users MUST NOT access the catalog APIs.

#### Scenario: Tenant admin creates a catalog item

- **WHEN** a tenant admin creates a Zubehör catalog item with name "Thermopapier" and default quantity 2
- **THEN** the item is stored for the active Verleiher
- **AND** it appears in the catalog list for that tenant

#### Scenario: Default quantity is optional on catalog items

- **WHEN** a tenant admin creates a catalog item with name "Netzwerkkabel" and no default quantity
- **THEN** the item is stored with a null default quantity

#### Scenario: Organisation user cannot manage the catalog

- **WHEN** an organisation admin or member attempts to create or list catalog items
- **THEN** the system rejects the request as forbidden

### Requirement: Rental Zubehör lines are manual and support catalog pick or free text

Each rental MAY have zero or more Zubehör lines. Lines MUST be added only by explicit tenant-admin action; creating a rental MUST NOT auto-insert catalog items. A line MUST have a label and MAY have an optional quantity. A line MAY reference a catalog item; when created from the catalog, the label MUST be copied from the catalog name at creation time. A line MAY be free text with no catalog reference.

#### Scenario: Pick from catalog creates a line with snapshotted label

- **WHEN** a tenant admin adds catalog item "Thermopapier" (default quantity 2) to a rental
- **THEN** a rental Zubehör line exists with label "Thermopapier", quantity 2, and a reference to that catalog item

#### Scenario: Free-text line without catalog reference

- **WHEN** a tenant admin adds a free-text Zubehör line with label "Verlängerungskabel 5m" and quantity 3
- **THEN** the line is stored with that label and quantity
- **AND** no catalog item reference is required

#### Scenario: New rental has no Zubehör lines

- **WHEN** a tenant admin creates an empty rental
- **THEN** the rental has zero Zubehör lines until lines are added explicitly

#### Scenario: Line quantity may be omitted

- **WHEN** a tenant admin adds a Zubehör line with a label but no quantity
- **THEN** the line is stored with a null quantity

#### Scenario: Catalog rename does not rewrite existing rental lines

- **WHEN** a catalog item name is changed after lines were created from it
- **THEN** existing rental lines keep their stored label

### Requirement: Catalog add may override quantity

When a tenant admin adds a Zubehör line from the catalog, the system SHALL allow an optional quantity override. If omitted, the catalog item’s default quantity MUST be used (including null when the catalog has no default). The UI SHOULD prefill the override field from the catalog default when selecting an item.

#### Scenario: Quantity override on catalog add

- **WHEN** a tenant admin adds catalog item "Thermopapier" (default quantity 2) with quantity 7
- **THEN** the rental Zubehör line is stored with quantity 7
- **AND** the label remains the catalog snapshot name

#### Scenario: Omitted override uses catalog default

- **WHEN** a tenant admin adds the same catalog item without a quantity override
- **THEN** the line quantity equals the catalog default quantity (2)

### Requirement: Zubehör lines are scoped to the rental tenant

List, add, update, and delete of rental Zubehör lines MUST be allowed only for rentals belonging to the active Verleiher and only by tenant admins (or platform admin with active Verleiher).

#### Scenario: Cross-tenant line access is denied

- **WHEN** a tenant admin requests Zubehör lines for a rental belonging to another Verleiher
- **THEN** the system responds with not found or forbidden
