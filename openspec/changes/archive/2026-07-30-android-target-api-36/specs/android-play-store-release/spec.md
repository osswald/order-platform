## ADDED Requirements

### Requirement: Play release targets API level 36

The Waiter Android app release build submitted to Google Play SHALL set both `compileSdk` and `targetSdk` to Android API level 36 (Android 16) or higher so new app updates meet Google Play’s target API level policy for phone and tablet form factors.

#### Scenario: Release Gradle config meets Play target

- **WHEN** `android/app/build.gradle.kts` is used to produce a Play release AAB
- **THEN** `compileSdk` SHALL be 36 or higher
- **AND** `targetSdk` SHALL be 36 or higher

#### Scenario: Existing minSdk unchanged by this policy

- **WHEN** the Play target API level is raised to 36
- **THEN** `minSdk` MAY remain at its existing Tap to Pay–compatible value (33)
- **AND** raising `minSdk` is not required for Play target-API compliance
