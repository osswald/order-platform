## ADDED Requirements

### Requirement: Release CI SDK setup uses published packages only
The Android release GitHub Actions workflow SHALL set up the Android SDK using only packages that current `sdkmanager` can resolve. The workflow MUST NOT depend on the obsolete standalone SDK `tools` package. After SDK setup, the workflow MUST still be able to install the platform API level required for the Waiter release build (API 36) and complete `bundleRelease`.

#### Scenario: SDK setup succeeds without obsolete tools
- **WHEN** a maintainer runs the Android release workflow on a runner whose `sdkmanager` no longer lists package `tools`
- **THEN** the SDK setup step succeeds without requesting `tools`

#### Scenario: Platform 36 remains available for the release build
- **WHEN** SDK setup has completed successfully
- **THEN** the workflow can install `platforms;android-36` (or equivalent) and proceed to build the signed release AAB
