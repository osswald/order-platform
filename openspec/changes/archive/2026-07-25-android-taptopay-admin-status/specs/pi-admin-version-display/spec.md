## ADDED Requirements

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
