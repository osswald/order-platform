## ADDED Requirements

### Requirement: Terminal init uses locale configuration

When the Android waiter app initializes the Stripe Terminal SDK, it SHALL use the `Terminal.init` overload that accepts a `LocaleConfig`, and SHALL pass a locale configuration that prefers the cardholder’s preferred language when available (falling back to the application/device locale), so Tap to Pay attestation and Terminal API error messages are not forced to English-only defaults introduced in Terminal Android SDK 5.6.0+.

#### Scenario: Init supplies LocaleConfig

- **WHEN** `AndroidTerminal` initializes Stripe Terminal for Tap to Pay
- **THEN** initialization SHALL call `Terminal.init` with a non-null `LocaleConfig`
- **AND** the configuration SHALL be `LocaleConfig.CardLanguagePreferenceIfAvailable` (or an equivalent that preserves card/app locale preference rather than hardcoding `en-US` only)

#### Scenario: Deprecated no-locale init is not used

- **WHEN** Terminal is initialized in production or debug builds
- **THEN** the app MUST NOT rely solely on the deprecated `Terminal.init` overload that omits `LocaleConfig` as the permanent init path
