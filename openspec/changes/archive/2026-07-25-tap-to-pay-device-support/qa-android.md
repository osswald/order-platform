# Manual Android QA — Tap to Pay device support

Prerequisites: event with `stripe_terminal`, organisation Stripe Connect ready, cloud reachable.

| Check | Expected |
|-------|----------|
| Supported phone (NFC + GMS, location granted) | **Karte** enabled; collect completes |
| Unsupported / NFC-off device | **Karte** disabled; hint «Gerät unterstützt keine Kartenzahlung (Tap to Pay).» |
| Location permission denied | **Karte** disabled; location hint |
| Browser PWA (no Android app) | **Karte** disabled; «Nur in der Android-App verfügbar.» |
| Older APK without `supportsTapToPay` | **Karte** still enabled when Android + cloud OK (fail open) |

Unit coverage: `pi/frontend` Vitest for `androidTerminal`, `stripeTerminalAvailability`, `resolvePayment`.
