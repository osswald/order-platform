## Purpose

Ensure the cloud admin UI loads and navigates quickly by constraining initial JavaScript/CSS payload, deferring heavy routes, and avoiding serial full-collection fetches on common screens.

## Requirements

### Requirement: Initial authenticated shell loads without heavy route modules

The production cloud admin bundle MUST NOT require downloading Event Stats charts, Help markdown rendering, or Orderjutsu import modules as part of the initial authenticated shell. Those features MUST load only when their routes (or explicitly deferred entry points) are entered.

#### Scenario: First visit to dashboard after login

- **WHEN** an authenticated operator opens `/dashboard` after a cold load
- **THEN** the network does not transfer the Event Stats chart library, Help markdown renderer, or Orderjutsu import wizard modules before those routes are visited
- **AND** the dashboard remains fully usable

#### Scenario: Navigating to event stats

- **WHEN** the operator opens an event stats route
- **THEN** the stats page and its chart dependencies load successfully
- **AND** charts render with the same data contract as before this change

### Requirement: Component library payload is limited to used UI

The cloud admin build MUST NOT register the entire Vuetify component and directive catalogs eagerly. Only components and directives used by the application MAY be included in production assets (via build-time auto-import or equivalent).

#### Scenario: Production build excludes unused Vuetify surface

- **WHEN** a production frontend build completes
- **THEN** the main JavaScript/CSS assets are smaller than the pre-change monolithic registration approach
- **AND** screens that use Vuetify controls (tables, dialogs, forms, navigation) continue to render correctly

### Requirement: Icon assets are limited to icons in use

The cloud admin MUST ship icon assets for icons referenced by the application, not a full Material Design Icons webfont catalog.

#### Scenario: Common screens render icons without full webfont

- **WHEN** an operator views navigation and list screens that show icons
- **THEN** those icons display correctly
- **AND** the browser does not need to download a multi-hundred-kilobyte full MDI webfont as the primary icon delivery mechanism

### Requirement: Independent bootstrap fetches run concurrently

Where authenticated bootstrap or list-page mounts issue multiple independent API requests, the client MUST start those requests concurrently rather than awaiting them strictly in series, unless a later request truly depends on an earlier response.

#### Scenario: Auth session and organisation list

- **WHEN** the authenticated app shell initializes session and accessible organisations
- **THEN** independent fetches overlap in flight when neither response is required as input to the other
- **OR** a documented dependency justifies sequencing (e.g. organisations require a valid session token that is not yet available)

#### Scenario: Articles page mount

- **WHEN** the Articles page mounts and needs categories, articles, and ingredient catalog data that do not depend on each other
- **THEN** those requests are started concurrently
- **AND** the page reaches a usable loaded state without artificial serial delays

#### Scenario: Event stats page mount

- **WHEN** the Event Stats page mounts and needs event, configuration, articles, and stats payloads that can be partially parallelized
- **THEN** independent requests overlap
- **AND** dependent requests still wait only on their true prerequisites

### Requirement: Org-scoped lists prefer active organisation when the API supports it

List screens that currently download tenant-wide collections and filter to the active organisation in the browser MUST request the active organisation scope from the API when a supported filter already exists, so payloads match the operator’s current context.

#### Scenario: Waiters list for active organisation

- **WHEN** the operator views Waiters with an active organisation selected
- **AND** the waiters API supports an organisation filter
- **THEN** the client requests waiters for that organisation
- **AND** the table shows the same membership set as today’s client-side filter for that organisation

#### Scenario: Unsupported filter remains client-side until API exists

- **WHEN** a list API has no organisation (or equivalent) filter
- **THEN** the client MAY continue client-side filtering for that screen
- **AND** this change MUST NOT invent breaking list API contracts solely for pagination
