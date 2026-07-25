## Why

Field support has no way to tell, from a waiter device, whether Stripe Tap to Pay will actually work before a real card is presented — a failed tap at the till is the first signal. The Pi Admin hub already shows the frontend and Pi backend versions, but not the native Android app version or any Tap to Pay readiness, so diagnosing "why can't this device take cards?" means guessing between wrong app build, missing permission, incompatible hardware, or cloud being down.

## What Changes

- Add a native **Android app version** line (APK `versionName` / `versionCode`) to the Pi Admin hub, shown only inside the Android wrapper.
- Add a **Tap to Pay readiness** status line to the Pi Admin hub that reflects device capability, location permission, and native bridge presence — labelled as device readiness, not a payment guarantee.
- Add a native bridge method so the PWA can read the app version and run a non-charging Tap to Pay capability check (`Terminal.supportsReadersOfType` + location + init), returning a structured result.
- Run the readiness check **when the Admin page loads** (not at cold app startup), so the location-permission prompt has already settled and the SDK can init in the foreground; re-run on each Admin open.
- Keep the existing App (PWA) and Pi (backend) version lines unchanged; the two new lines appear beneath them and degrade gracefully off-Android.

## Capabilities

### New Capabilities
- `pi-admin-taptopay-status`: Native Tap to Pay device-readiness check (bridge contract + Admin-load trigger) and its status display in the Pi Admin hub.

### Modified Capabilities
- `pi-admin-version-display`: Admin hub additionally shows the native Android app version (APK `versionName`) when running inside the Android wrapper.

## Impact

- **Android app**: new/extended JS bridge (`StripeTerminalBridge` or a small app-info bridge) exposing `getAppInfo()` and a `checkTapToPaySupport()` that calls `Terminal.supportsReadersOfType` without collecting a payment; `MainActivity` wiring; `BuildConfig.VERSION_NAME`/`VERSION_CODE`.
- **Pi frontend**: `AdminHubView.vue` gains two conditional lines; new util wrapping the bridge (mirrors `androidTerminal.ts` / `stripeTerminalAvailability.ts`); i18n de/en strings; Vitest coverage.
- **No cloud backend / API / OpenAPI changes** — status is device-local; existing `/health` and `/v1/cloud/reachable` are reused only if cloud state is added later (out of scope here).
- **Docs**: note the Admin readiness line and its "device-only" meaning in `android/README.md` / `docs/stripe-connect-terminal.md`.
