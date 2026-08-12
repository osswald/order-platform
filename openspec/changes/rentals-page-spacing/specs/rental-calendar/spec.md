## ADDED Requirements

### Requirement: Calendar page uses shared cloud admin page inset

The rentals calendar surface SHALL use the same page inset as other cloud admin pages (shared page chrome), so content is not flush to the main content area edges. The calendar MUST NOT wrap in list-detail panel/card chrome solely for spacing; calendar grids and dialogs remain unchanged in behavior.

#### Scenario: Desktop main content has inset around the calendar

- **WHEN** a hire-company admin opens the rentals calendar route on a desktop-width viewport
- **THEN** the page title, toolbar, and calendar content sit inside the shared page inset
- **AND** content is not flush against the left or right edges of the main content area

#### Scenario: Narrow viewport keeps comfortable inset

- **WHEN** a hire-company admin opens the rentals calendar route on a narrow (mobile-width) viewport
- **THEN** the page still uses the shared responsive page inset
- **AND** content is not flush against the main content edges
