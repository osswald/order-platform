## 1. Tests first (Pi frontend)

- [x] 1.1 Add Vitest for `androidAppInfo` util: returns `{ versionName, versionCode }` from bridge; returns unavailable when bridge/method missing; parses string/object results (mirror `androidTerminal` bridge-mock style)
- [x] 1.2 Add Vitest for the Tap to Pay readiness util: maps bridge results to `ready` / `ready_simulated` / `location_missing` / `unsupported` / `error` / `unavailable`; handles thrown bridge errors
- [x] 1.3 Extend `AdminHubView.test.ts`: shows Android version line only on Android; shows Tap to Pay status line only on Android; shows neutral "checking" state before the async result resolves; re-runs check on mount

## 2. Pi frontend implementation

- [x] 2.1 Add `pi/frontend/src/utils/androidAppInfo.ts` wrapping `window.AndroidApp.getAppInfo()` (bridge/call/parse pattern from `androidTerminal.ts`) and extend `src/env.d.ts` window typings
- [x] 2.2 Add Tap to Pay readiness util (e.g. `src/utils/taptoPayStatus.ts`) wrapping `window.AndroidTerminal.checkTapToPaySupport()` and returning a typed status
- [x] 2.3 Update `AdminHubView.vue`: on mount (alongside `/health` + `/setup/status`) run both checks behind `isAndroidApp()`; render `Android v…` and `Tap to Pay: …` lines with a pending state; keep existing App/Pi lines unchanged
- [x] 2.4 Add de/en i18n strings for the Android version label and each Tap to Pay status code (ready, simulated, location missing, unsupported, error)

## 3. Android native bridge

- [x] 3.1 Add an `AndroidApp` JS bridge exposing `getAppInfo()` → `{ ok, versionName, versionCode }` from `BuildConfig.VERSION_NAME` / `VERSION_CODE`; register it in `MainActivity` via `addJavascriptInterface(..., "AndroidApp")`
- [x] 3.2 Add `checkTapToPaySupport()` to `StripeTerminalBridge` that ensures `Terminal.init`, calls `supportsReadersOfType(TAP_TO_PAY, TapToPayDiscoveryConfiguration(isSimulated = BuildConfig.DEBUG))` without collecting payment, checks location permission, and returns a structured JSON status (`ready`/`ready_simulated`/`location_missing`/`unsupported`/`error`)
- [x] 3.3 Ensure the check never throws to the WebView (catch `TerminalException`/exceptions → `unsupported`/`error`) and does not alter the existing `collectPayment` init path

## 4. Docs and verification

- [x] 4.1 Document the Admin native-version and Tap to Pay readiness line (and its device-only meaning) in `android/README.md` and/or `docs/stripe-connect-terminal.md`
- [x] 4.2 Run Pi frontend tests (`cd pi/frontend && npm test`) and `./scripts/lint.sh --staged`; build the Pi frontend
- [x] 4.3 Manual check on an Android device/emulator: Admin shows correct app version; readiness shows `ready`/`ready_simulated` on a supported device, `location_missing` before granting location, and a sensible status on an unsupported device
