## Why

On Android (WebView edge-to-edge), fullscreen waiter POS surfaces — order, table payment, and the TWINT QR sheet — draw under the status bar / hole-punch and shrink-wrap to content, leaving a large empty void. Normal `app-main` screens already clear the safe area and look fine; fullscreen routes and fixed overlays do not inherit that padding and must self-manage insets and viewport height.

## What Changes

- Ensure fullscreen POS roots (`.order-screen`, `.split-pay-screen`) fill the visible viewport on Android and clear system bar / display-cutout insets (top and bottom).
- Ensure the TWINT QR fullscreen sheet (and other full-bleed fixed sheets used in the same flows, if needed) apply `--safe-top` as well as `--safe-bottom`.
- Make viewport fill work with and without emulated-printer / hosted-demo shell (Play Review Demo), where the current `height: 100%` ancestor chain breaks.
- Do not change layout of non-fullscreen hub / keypad / list screens that already look correct.

## Capabilities

### New Capabilities

- `pi-android-safe-layout`: Android WebView safe-area and fullscreen viewport fill for Pi waiter POS (order, payment, TWINT QR, and related full-bleed surfaces).

### Modified Capabilities

- (none)

## Impact

- Pi frontend: `app.css` Android fullscreen rules, hosted-demo height chain, `TwintQrSheet.vue` (and possibly other `position: fixed; inset: 0` sheets).
- Android app: existing `AndroidInsets` bridge remains the source of `--safe-*`; no API/backend changes expected.
- Manual verification on Android device (Play Review Demo and real venue Pi); Vitest/CSS regression coverage where practical.
