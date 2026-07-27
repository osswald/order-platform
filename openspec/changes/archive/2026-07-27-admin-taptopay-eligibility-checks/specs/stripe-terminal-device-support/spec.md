## ADDED Requirements

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
