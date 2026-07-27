## Why

Pi Admin already shows a coarse Tap to Pay line (`bereit` / `Standort fehlt` / `nicht unterstützt` / …), but field support cannot see *which* Stripe device requirements failed. Diagnosing an unsupported phone means guessing between NFC, Android version, GMS, keystore, location, developer options, and other soft criteria.

## What Changes

- Extend the Android Tap to Pay readiness bridge so a failed (or incomplete) check returns a structured list of eligibility checks with pass/fail for each.
- In Pi Admin (Android only), when Tap to Pay is not fully ready, show that checklist with OK / not-OK per item — including checks that passed — so support can see the full picture.
- When every check passes (ready / ready simulated), keep the existing single status line and do **not** list the checks.
- Prefer locally verifiable Stripe Tap to Pay criteria plus the existing location-permission gate; keep the Stripe SDK overall result as one check among them.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `pi-admin-taptopay-status`: When readiness is not OK, Admin SHALL list eligibility checks with pass/fail; hide the list when all checks pass.
- `stripe-terminal-device-support`: Bridge readiness payload SHALL include a structured per-check eligibility breakdown when used for Admin diagnostics (without changing payment-picker fail-open behaviour for older APKs).

## Impact

- **Android**: `StripeTerminalBridge` (and helpers) evaluate and serialise eligibility checks; may touch `MainActivity` only if wiring changes.
- **Pi frontend**: `taptoPayStatus.ts`, `AdminHubView.vue` (+ tests); German Admin labels for each check.
- **Docs**: `docs/stripe-connect-terminal.md` Admin section briefly notes the checklist.
- No cloud API, Pi backend, or Stripe Connect changes.
