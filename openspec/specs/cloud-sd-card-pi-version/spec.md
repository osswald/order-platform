# cloud-sd-card-pi-version Specification

## Purpose

Show the Pi backend app version reported by each paired SD card on the cloud server-appliance SD-card list, so operators can see which release is running without visiting Pi Admin.

## Requirements

### Requirement: Pi reports backend app version on edge requests

Paired Pi backends SHALL include their running backend app version on authenticated requests to the cloud edge API. The version SHALL be the same deployed semver the Pi exposes locally (from image/`APP_VERSION`). The Pi MAY also include a build timestamp when available.

#### Scenario: Authenticated edge request carries app version

- **WHEN** a paired Pi backend calls an authenticated cloud edge endpoint
- **THEN** the request SHALL include the Pi backend app version metadata
- **AND** that version SHALL match the value the Pi would report on its local health/version endpoint for the same process

#### Scenario: Build time optional

- **WHEN** the Pi backend has a non-empty build timestamp configured
- **THEN** the edge request MAY include that build timestamp along with the app version

### Requirement: Cloud stores latest reported version per SD-card credential

On successful edge authentication, when the request includes a non-empty Pi backend app version, the cloud SHALL persist that version (and build timestamp when provided) on the corresponding edge credential. Missing version metadata SHALL NOT clear a previously stored value. Invalid or empty version metadata SHALL NOT cause the authenticated request to fail.

#### Scenario: Version persisted with last seen

- **WHEN** an authenticated edge request includes a non-empty app version for an active credential
- **THEN** cloud SHALL update that credential’s stored reported app version
- **AND** SHALL continue to update `last_seen_at` as today

#### Scenario: Older Pi without version metadata

- **WHEN** an authenticated edge request omits app version metadata
- **THEN** cloud SHALL still authenticate and process the request
- **AND** SHALL leave any previously stored reported version unchanged

#### Scenario: Bad telemetry does not break auth

- **WHEN** an authenticated edge request includes empty or unusable version metadata
- **THEN** cloud SHALL NOT fail the request solely because of that metadata
- **AND** SHALL leave stored reported version unchanged when the version is empty/unusable

### Requirement: Cloud appliance API exposes reported version on edge credentials

Appliance detail responses that include edge credentials SHALL expose each credential’s latest reported app version and build timestamp (nullable when never reported).

#### Scenario: Credential with reported version

- **WHEN** an authorized client fetches a server appliance that has an edge credential with a stored reported app version
- **THEN** the edge credential payload SHALL include that reported app version
- **AND** SHALL include the reported build timestamp when one was stored

#### Scenario: Credential never reported

- **WHEN** an edge credential has never successfully reported an app version
- **THEN** the reported app version fields in the API SHALL be null or absent equivalently

### Requirement: Cloud SD-card table shows reported Pi version

The cloud Appliances UI SD-card list for a server appliance SHALL show each credential’s reported Pi backend app version. When no version has been reported, the UI SHALL show an empty/unavailable indicator without blocking other credential actions.

#### Scenario: Version visible next to last seen

- **WHEN** an administrator views the SD Cards table for a server appliance and a credential has a reported app version
- **THEN** the table SHALL display that version (including build time when available, consistent with Pi Admin backend formatting conventions)

#### Scenario: Never reported shows unavailable

- **WHEN** an administrator views the SD Cards table and a credential has no reported app version
- **THEN** the version cell SHALL indicate unavailable/empty
- **AND** status, last seen, and revoke/delete actions SHALL still work
