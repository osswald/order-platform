## ADDED Requirements

### Requirement: Cloud admin post-login and context-reload navigation stays same-origin
The cloud admin UI MUST only navigate via `window.location` (including `assign` and `href`) to URLs that share the current page origin. A login `redirect` query value, Vue Router `route.path`, or any other client-supplied string MUST be rejected when it is protocol-relative (`//…`), has a different origin, uses a non-http(s) scheme, or is not a string. Rejected values MUST fall back to a known in-app path (`/dashboard` after login; the current sanitized in-app path for organisation or hire-company hard-reloads). Checking `startsWith('/')` alone is not sufficient.

#### Scenario: Login rejects protocol-relative redirect
- **WHEN** a user completes login with `?redirect=//evil.example`
- **THEN** the admin UI does not assign `window.location` to that value
- **AND** navigation falls back to `/dashboard`

#### Scenario: Login accepts a same-origin relative path
- **WHEN** a user completes login with `?redirect=/events`
- **THEN** the admin UI navigates to the same-origin path `/events`

#### Scenario: Organisation context reload does not assign an off-origin path
- **WHEN** the admin UI hard-reloads after an organisation or hire-company context change
- **THEN** `window.location.assign` is called only with a same-origin relative path
- **AND** values that would resolve to another origin or a `javascript:` URL are not assigned
