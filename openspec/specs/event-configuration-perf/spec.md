# event-configuration-perf Specification

## Purpose
TBD - created by archiving change fix-event-configuration-perf. Update Purpose after archive.
## Requirements
### Requirement: Configuration loads without cartesian relationship joins

The cloud backend MUST load an event for configuration using relationship loading that does not join multiple collections in a single SQL statement (e.g. `selectinload` for collections). GET `/events/{event_id}/configuration` (with or without `fields=summary`) and PUT `/events/{event_id}/configuration` MUST return the same response schemas as today.

#### Scenario: Full configuration read returns stations and layout cells

- **WHEN** a client requests GET `/events/{event_id}/configuration` without `fields=summary` for an event that has stations with articles and an app layout with cells
- **THEN** the response includes those station `article_ids` and layout `cells` with their `article_ids`
- **AND** the server does not use a multi-collection `joinedload` graph for that read

#### Scenario: Summary configuration omits layout cells

- **WHEN** a client requests GET `/events/{event_id}/configuration?fields=summary`
- **THEN** app layout entries are present but their `cells` arrays are empty (or omitted per existing summary behavior)
- **AND** station configuration including `article_ids` remains present

#### Scenario: Configuration save returns successfully under proxy-friendly duration

- **WHEN** a client PUTs a valid configuration for a venue-sized event (multiple stations, layout cells, waiters, registers)
- **THEN** the API responds with HTTP 200 and an `EventConfigurationRead` body
- **AND** the handler does not perform a second multi-collection `joinedload` reload that would typically exceed reverse-proxy timeouts

### Requirement: Station article tree is available for layout cell editing

The system MUST provide the set of non-addition articles assigned to any station of the event for use in the layout-cell editor, without requiring a full configuration relationship graph load.

#### Scenario: Tree reflects station articles

- **WHEN** an event has articles assigned to one or more stations
- **AND** the client requests the station article tree (API and/or equivalent client-built tree from station assignments)
- **THEN** those articles appear as selectable leaves grouped by category
- **AND** addition (`is_addition`) articles are excluded

#### Scenario: Empty stations yield empty tree with clear UI

- **WHEN** an event has no station articles
- **AND** the operator opens the layout cell editor article picker
- **THEN** the UI shows an explicit empty state (not a blank filter-only area with no explanation)

#### Scenario: Tree load failure is visible

- **WHEN** loading articles for the layout cell picker fails
- **THEN** the UI shows an error or retry affordance
- **AND** the failure is not silently ignored

### Requirement: App layouts tab does not block indefinitely on configuration load

The cloud admin App-Layouts section MUST load layout cells in a way that completes promptly once the configuration loader is efficient, and MUST show loading or error feedback while cells are loading.

#### Scenario: Layouts tab shows grid after cells load

- **WHEN** the operator opens the App-Layouts section for an event with a saved layout and cells
- **THEN** after the cells load completes, the layout grid is visible with cell labels
- **AND** a loading indicator is shown while cells are in flight
- **AND** a load failure surfaces an error message rather than an endless blank section

