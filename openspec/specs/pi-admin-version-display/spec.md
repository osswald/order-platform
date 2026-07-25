# pi-admin-version-display Specification

## Purpose
Define how Pi Admin shows both the bundled frontend app version and the live Pi backend version.

## Requirements

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

### Requirement: Pi Admin shows native Android app version

When the Pi PWA runs inside the native Android wrapper, the Pi Admin hub SHALL display the native Android application version (APK `versionName`) in addition to the existing frontend and Pi backend version lines.

#### Scenario: Android app version visible in Admin on Android

- **WHEN** an administrator opens the Pi Admin hub inside the Android wrapper and the native app-info bridge is available
- **THEN** the UI SHALL show the native Android app version (`versionName`, e.g. `Android v1.5.10`)
- **AND** it SHALL continue to show the frontend app version and the Pi backend version lines unchanged

#### Scenario: Android version line hidden outside the Android app

- **WHEN** the Pi Admin hub is opened in a normal browser (no native app-info bridge)
- **THEN** the UI SHALL NOT show a native Android app version line
- **AND** the frontend and Pi backend version lines SHALL still be shown

#### Scenario: Native app version unavailable

- **WHEN** the administrator opens Pi Admin inside the Android wrapper but the native app version cannot be read
- **THEN** the UI SHALL still show the frontend and Pi backend version lines
- **AND** the UI SHALL NOT block admin access
