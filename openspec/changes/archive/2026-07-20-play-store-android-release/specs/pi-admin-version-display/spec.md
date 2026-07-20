## ADDED Requirements

### Requirement: Pi backend exposes its running version

The Pi backend SHALL expose its deployed version (semver from repo `VERSION` and optional build timestamp) via a read-only API endpoint accessible to the Pi frontend.

#### Scenario: Version endpoint returns backend version

- **WHEN** a client requests the Pi backend version endpoint (e.g. `GET /v1/health` with version fields or `GET /v1/version`)
- **THEN** the response SHALL include the backend semver and MAY include a build timestamp matching the Docker image build

#### Scenario: Version matches deployed image

- **WHEN** the Pi backend runs from a Docker image built with `VERSION` `1.2.3` and build time `202607201045`
- **THEN** the version endpoint SHALL report `1.2.3` and build time `202607201045` (or equivalent normalized format)

### Requirement: Pi Admin shows frontend and backend versions

The Pi Admin hub SHALL display both the bundled frontend app version and the Pi backend version currently running on the device.

#### Scenario: Both versions visible in Admin

- **WHEN** an administrator opens the Pi Admin hub and the Pi backend is reachable
- **THEN** the UI SHALL show the frontend app version (from `useAppVersion()`)
- **AND** the UI SHALL show the Pi backend version fetched from the API

#### Scenario: Frontend version unchanged

- **WHEN** the Pi Admin hub displays version information
- **THEN** the frontend version label SHALL continue to reflect the bundled Pi PWA build (`VITE_APP_VERSION` / build time)

#### Scenario: Backend unreachable

- **WHEN** an administrator opens Pi Admin and the backend version cannot be fetched
- **THEN** the UI SHALL still show the frontend app version
- **AND** the UI SHALL indicate that the Pi backend version is unavailable (without blocking admin access)
