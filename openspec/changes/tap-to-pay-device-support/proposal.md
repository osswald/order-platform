## Why

Waiters currently see **Karte** enabled whenever they are in the Android app and cloud is reachable, even on phones that cannot run Stripe Tap to Pay (no NFC, unsupported OS/hardware, missing GMS, etc.). Failure only appears at collect time. Stripe’s Terminal SDK already exposes a fast runtime check (`supportsReadersOfType`); we should surface that before the waiter tries to take a card payment.

## What Changes

- Expose a native Android bridge API that reports whether the **current device** supports Tap to Pay (via Stripe Terminal `supportsReadersOfType` for `TAP_TO_PAY`).
- Use that result in the Pi PWA payment picker so **Karte** is disabled with a clear hint when the device is unsupported.
- Keep existing gates (Android app present, cloud reachable) and add device support as an additional gate.
- Document the capability check and its limits (some Stripe criteria still fail only at discover/connect).
- **Not BREAKING** for payment payload shape or cloud/Pi Terminal APIs.

## Capabilities

### New Capabilities

- `stripe-terminal-device-support`: Runtime detection of Tap to Pay device support on Android and use of that signal to enable/disable the waiter **Karte** payment option with an appropriate hint.

### Modified Capabilities

- (none — no existing living spec covers Terminal Tap to Pay availability)

## Impact

- **Android app**: `StripeTerminalBridge.kt` (and possibly `MainActivity` permission timing); bridge contract for the PWA.
- **Pi frontend**: `androidTerminal.ts`, `stripeTerminalAvailability.ts`, payment picker / resolve-payment tests and German hint copy.
- **Docs**: `docs/stripe-connect-terminal.md`, optionally `android/README.md`.
- **Cloud / Pi backends**: no API or schema changes expected.
- **Dependencies**: existing Stripe Terminal Android SDK (`stripeterminal-core` / `stripeterminal-taptopay`); no new packages expected.
