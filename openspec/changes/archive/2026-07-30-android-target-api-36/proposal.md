## Why

Google Play requires new apps and app updates to target Android 16 (API level 36) from 31 August 2026. Play Console already warns that the Vendiqo Waiter app (`ch.vendiqo.app`) targets API 35. Bumping now, together with Stripe Terminal to the current SDK, keeps the next Play upload compliant and picks up Tap to Pay fixes without a second release scramble.

## What Changes

- Raise Android `compileSdk` and `targetSdk` from 35 to **36**
- Upgrade Stripe Terminal Android artifacts (`stripeterminal-core`, `stripeterminal-taptopay`) from **5.5.1** to **5.7.0**
- Update `Terminal.init` to the `LocaleConfig` overload so Tap to Pay attestation / API error messages follow app or cardholder locale preference (5.6.0 deprecated the old overload; Tap to Pay attestation otherwise defaults to `en-US`)
- Refresh Android README / docs that still say API 35 (and any stale minSdk notes)

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `android-play-store-release`: Release builds submitted to Google Play MUST target API level 36 (Android 16) or higher
- `stripe-terminal-device-support`: Terminal initialization SHALL use the current SDK init API with locale configuration so Tap to Pay / Terminal user-facing errors are not forced to English-only defaults

## Impact

- **Android app**: `android/app/build.gradle.kts`, `StripeTerminalBridge.kt` (`Terminal.init`), possibly `android/README.md` / `docs/stripe-connect-terminal.md`
- **Dependencies**: Stripe Terminal `5.7.0` (skip 5.6.0 offline DB migration bug by jumping straight to 5.7.0)
- **Play / CI**: Release AAB workflow unchanged in structure; must produce a targetSdk 36 artifact
- **QA**: Tap to Pay on a real tablet; edge-to-edge / insets (already implemented); tablet rotate / multi-window smoke on `sw600dp+` (API 36 large-screen adaptive rules)
- **Out of scope**: Pi frontend feature work, minSdk changes, Play listing copy beyond what the build requires
