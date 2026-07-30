# stripe-terminal-device-support Specification

## Purpose
Runtime detection of Tap to Pay device support on Android and use of that signal to enable/disable the waiter **Karte** payment option with an appropriate hint.

## Requirements

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

### Requirement: Bridge returns structured Tap to Pay eligibility checks

`AndroidTerminal.supportsTapToPay()` SHALL include a `checks` array of eligibility probes when evaluating Tap to Pay readiness. Each entry SHALL have a stable `id`, an `ok` boolean, and MAY include a human-readable `detail` string. The existing top-level fields (`ok`, `supported`, `code`, `error`, `simulated`) SHALL remain valid for callers that ignore `checks`.

#### Scenario: Checks present when device is unsupported

- **WHEN** `supportsTapToPay()` runs and Tap to Pay is not fully supported (or location permission is missing)
- **THEN** the JSON response SHALL include a `checks` array with one entry per evaluated criterion
- **AND** each failed criterion SHALL have `ok: false`
- **AND** each passed criterion SHALL have `ok: true`

#### Scenario: Checks cover documented local criteria plus SDK result

- **WHEN** `supportsTapToPay()` evaluates eligibility
- **THEN** the `checks` array SHALL include, at minimum, entries for location permission, Android version (13+), NFC, hardware keystore, Google Mobile Services / Play Store presence, security patch freshness, developer-options state (release builds), internet connectivity (best-effort), and the Stripe SDK `supportsReadersOfType` outcome (`sdk_support`)
- **AND** check `id` values SHALL be stable machine-readable strings suitable for UI labelling

#### Scenario: Payment picker ignores checks

- **WHEN** the Pi payment picker evaluates Tap to Pay device support
- **THEN** it SHALL continue to use the existing top-level `supported` / location / error fields
- **AND** it MUST NOT require the `checks` array to enable or disable Karte

### Requirement: Terminal init uses locale configuration

When the Android waiter app initializes the Stripe Terminal SDK, it SHALL use the `Terminal.init` overload that accepts a `LocaleConfig`, and SHALL pass a locale configuration that prefers the cardholder’s preferred language when available (falling back to the application/device locale), so Tap to Pay attestation and Terminal API error messages are not forced to English-only defaults introduced in Terminal Android SDK 5.6.0+.

#### Scenario: Init supplies LocaleConfig

- **WHEN** `AndroidTerminal` initializes Stripe Terminal for Tap to Pay
- **THEN** initialization SHALL call `Terminal.init` with a non-null `LocaleConfig`
- **AND** the configuration SHALL be `LocaleConfig.CardLanguagePreferenceIfAvailable` (or an equivalent that preserves card/app locale preference rather than hardcoding `en-US` only)

#### Scenario: Deprecated no-locale init is not used

- **WHEN** Terminal is initialized in production or debug builds
- **THEN** the app MUST NOT rely solely on the deprecated `Terminal.init` overload that omits `LocaleConfig` as the permanent init path
