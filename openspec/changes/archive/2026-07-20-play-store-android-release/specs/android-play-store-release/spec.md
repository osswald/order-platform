## ADDED Requirements

### Requirement: Release AAB build from monorepo VERSION

The Android release build SHALL produce a signed App Bundle (`.aab`) whose `versionName` matches the repository root `VERSION` file and whose `versionCode` is derived deterministically from that semver without a static suffix.

#### Scenario: Version aligns with repo release

- **WHEN** `VERSION` contains `1.2.3` and `./gradlew bundleRelease` runs with valid signing configuration
- **THEN** the output AAB SHALL have `versionName` `1.2.3` and a monotonically increasing `versionCode` suitable for Google Play

### Requirement: GitHub Actions builds release AAB

The repository SHALL provide a GitHub Actions workflow that builds the Waiter Android release AAB on demand using JDK 17 and Node.js 24, bundling `pi/frontend` via the existing Gradle `preBuild` pipeline.

#### Scenario: Manual workflow dispatch

- **WHEN** a maintainer triggers the Android release workflow with a chosen Play track
- **THEN** the workflow SHALL run `./gradlew bundleRelease` and produce an uploadable AAB artifact

### Requirement: Release signing via GitHub secrets

The Android release workflow SHALL sign the AAB using credentials supplied as GitHub Actions secrets (upload keystore and passwords), without committing keystore material to the repository.

#### Scenario: Secrets present

- **WHEN** the workflow runs and required signing secrets are configured
- **THEN** the produced AAB SHALL be signed with the upload key registered in Play Console

#### Scenario: Secrets missing

- **WHEN** the workflow runs without required signing secrets
- **THEN** the workflow SHALL fail with a clear error before attempting Play upload

### Requirement: Upload to Google Play Console

The Android release workflow SHALL upload the signed AAB to Google Play using the Google Play Developer API and a service account JSON secret.

#### Scenario: Upload to internal testing

- **WHEN** the workflow is dispatched with track `internal`
- **THEN** the AAB SHALL be uploaded to the internal testing track for package `ch.vendiqo.app`

### Requirement: Single production APK defaults to venue LAN

The Play Store release build SHALL NOT override `VITE_API_BASE` at build time; the bundled Pi frontend default API base SHALL remain the venue LAN convention (`http://192.168.192.10` per `.env.android`).

#### Scenario: Default API base for venues

- **WHEN** a venue waiter installs the app from Play Store and opens it on the venue LAN
- **THEN** the app SHALL attempt to reach the Pi at the default LAN API base without requiring a separate review-only build flavor
