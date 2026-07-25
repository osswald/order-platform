## ADDED Requirements

### Requirement: Android bridge reports Tap to Pay device support

The Android waiter app SHALL expose a JavaScript bridge method `AndroidTerminal.supportsTapToPay()` that evaluates whether the current device can use Stripe Tap to Pay via the Stripe Terminal SDK (`supportsReadersOfType` for Tap to Pay).

#### Scenario: Supported device

- **WHEN** the Terminal SDK reports that Tap to Pay readers are supported on the device
- **THEN** `supportsTapToPay()` returns JSON with `ok: true` and `supported: true`

#### Scenario: Unsupported device

- **WHEN** the Terminal SDK reports that Tap to Pay readers are not supported on the device
- **THEN** `supportsTapToPay()` returns JSON with `ok: true` and `supported: false`
- **AND** the response MAY include an `error` string describing the SDK reason

#### Scenario: Cannot evaluate without location permission

- **WHEN** location permission required for Terminal is not granted
- **THEN** `supportsTapToPay()` returns JSON with `ok: false` and an error indicating location permission is required
- **AND** it MUST NOT claim `supported: false` solely because permission is missing

### Requirement: Payment picker disables Karte on unsupported devices

When an event offers `stripe_terminal`, the Pi PWA payment picker SHALL disable the **Karte** option when the Android device does not support Tap to Pay, and SHALL show a German hint explaining that the device cannot take card payments.

#### Scenario: Unsupported Android device with cloud online

- **WHEN** the waiter is in the Android app, cloud is reachable, and `supportsTapToPay` reports `supported: false`
- **THEN** the Karte picker entry is disabled
- **AND** the hint is «Gerät unterstützt keine Kartenzahlung (Tap to Pay).»

#### Scenario: Supported Android device with cloud online

- **WHEN** the waiter is in the Android app, cloud is reachable, and `supportsTapToPay` reports `supported: true`
- **THEN** the Karte picker entry is enabled
- **AND** no device-support hint is shown

#### Scenario: Existing gates still apply first

- **WHEN** the waiter is not in the Android app
- **THEN** the Karte picker entry remains disabled with «Nur in der Android-App verfügbar.»
- **WHEN** the waiter is in the Android app but cloud is unreachable
- **THEN** the Karte picker entry remains disabled with «Cloud-Verbindung erforderlich.»

#### Scenario: Older Android app without support API

- **WHEN** `AndroidTerminal` is present but `supportsTapToPay` is not available
- **THEN** the picker MUST NOT disable Karte solely for missing device-support information
- **AND** existing Android-app and cloud-reachability gates still apply

### Requirement: Support check uses simulated discovery in debug builds

Debug Android builds SHALL evaluate Tap to Pay support with the simulated Tap to Pay discovery configuration, consistent with collect-time reader discovery.

#### Scenario: Debug build support check

- **WHEN** `supportsTapToPay()` runs in a debug build
- **THEN** the SDK support check uses simulated Tap to Pay discovery configuration
