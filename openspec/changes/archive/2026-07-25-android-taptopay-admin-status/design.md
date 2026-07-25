## Context

The Pi PWA runs inside a native Android WebView (`MainActivity.kt`) that injects JS bridges: `AndroidPrinter`, `AndroidTerminal`, `AndroidInsets`, `AndroidNetwork`. Tap to Pay payments already run through `AndroidTerminal.collectPayment(...)` (`StripeTerminalBridge.kt`) using the Stripe Terminal Android SDK `5.5.1` (`stripeterminal-taptopay` + `-core`), `minSdk = 33`, location permission required and enforced in the bridge.

Today the Admin hub (`pi/frontend/src/views/admin/AdminHubView.vue`) shows two version lines:

- **App** — `useAppVersion()` (bundled PWA `VITE_APP_VERSION`)
- **Pi** — Pi backend `/health` (`version` + `build_time`)

Gaps:

- The native APK version (`BuildConfig.VERSION_NAME` / `VERSION_CODE`, derived from repo `VERSION`) is not exposed to the PWA at all.
- `AndroidTerminal.isAvailable()` only returns `Terminal.isInitialized()`, which is **false until the first payment** (init is lazy inside `collectPayment`), so it is useless as a readiness signal.
- Terminal readiness is layered (device capability → location → bridge → cloud → org/event config); the PWA only checks "bridge present / Android" to enable the Karte button, and everything else fails later at pay time.

Stripe provides `Terminal.supportsReadersOfType(...)` (~10 ms after SDK init) to check device hardware/OS compatibility for Tap to Pay without collecting a payment. This is the right primitive for a non-charging readiness check.

Constraints:

- No Stripe secrets on device; no PaymentIntent is created for the check.
- Production (non-simulated) discovery/connect refuses debuggable builds and developer options; capability check via `supportsReadersOfType` still works and is the safe check to run.
- The SDK must init while the app is in the foreground; the Admin page is a safe, user-initiated moment for that.

## Goals / Non-Goals

**Goals:**

- Show the native Android app version in Admin when running in the wrapper.
- Show a Tap to Pay **device-readiness** status in Admin, computed by a real (non-charging) SDK capability check plus location-permission state.
- Run the check when the Admin page loads (and re-run on each open), after the location prompt has settled.
- Degrade cleanly: off-Android the two new lines are hidden; on error the status is explanatory, never a hard failure that blocks Admin.

**Non-Goals:**

- Proving a real card charge will succeed (needs PaymentIntent + physical tap).
- Verifying the organisation's Stripe onboarding / event `stripe_terminal` config (cloud/token dependent — possible later layer, out of scope here).
- Any cloud backend, API, OpenAPI, or database change.
- Changing the charge flow, the Karte button gating, or `collectPayment`.
- iOS / React Native.

## Decisions

### 1. Readiness primitive: `supportsReadersOfType`, not `isInitialized`

- **Choice**: Add a bridge method that ensures `Terminal.init` (reuse the existing lazy init path) then calls `Terminal.supportsReadersOfType(deviceType = TAP_TO_PAY, discoveryConfiguration = TapToPayDiscoveryConfiguration(isSimulated = BuildConfig.DEBUG))` and maps the result to a structured status.
- **Why**: `supportsReadersOfType` is designed exactly for a fast, non-charging capability check (device hardware, Android 13+, hardware keystore). `isInitialized()` is meaningless before first pay.
- **Alternative rejected**: run `discoverReaders` — heavier, needs foreground reader service, and in production refuses debuggable builds; overkill for a status line.
- **Alternative deferred**: fetch a connection token + discover to prove the org path — needs `event_id`/location and cloud; a possible second layer later.

### 2. Status shape (structured, not a boolean)

Bridge returns JSON like existing bridges (`ok` + fields). Proposed readiness codes:

```
ready            device supports Tap to Pay, location granted
ready_simulated  debug build; capability OK via simulated reader
location_missing device capable but location permission not granted
unsupported      device/OS/keystore not capable (TerminalException)
error            init or check failed unexpectedly
unavailable      bridge/method not present (treated as "not Android")
```

- **Why**: Support needs to distinguish "wrong hardware" from "grant the permission" from "cloud/other". A single green/red dot hides the actionable case (location).

### 3. Trigger on Admin load, not cold startup

- **Choice**: Run the check in `AdminHubView`'s `onMounted` (alongside the existing `/health` and `/setup/status` fetches), and re-run on each Admin open. Cache the last result briefly in-memory to avoid re-init churn if Admin is reopened rapidly.
- **Why**: Cold startup races the location-permission dialog and may run before the user answers (false negatives). Admin open is user-initiated, foreground, and after first launch the permission is usually settled. Matches the user's request.
- **Trade-off**: First-ever Admin open right after install may still show `location_missing` until granted; acceptable and accurate.

### 4. App version via a dedicated getter

- **Choice**: Expose `getAppInfo()` returning `{ ok, versionName, versionCode }` from a bridge (either extend `AndroidTerminal` or add a tiny `AndroidApp` bridge). Prefer a small dedicated `AndroidApp` bridge so app metadata is not coupled to the Terminal bridge.
- **Why**: Clean separation; the version line should work even if Terminal is unsupported on the device.
- **Alternative**: bake version into the user-agent — brittle to parse and already crowded.

### 5. Frontend wiring mirrors existing utils

- **Choice**: New `pi/frontend/src/utils/androidAppInfo.ts` (version) and extend `androidTerminal.ts` / add `taptoPayStatus.ts` for the readiness call, following the `bridge()/call()/parseResult()` pattern already in `androidTerminal.ts`. `AdminHubView.vue` renders two extra `v-if="androidApp"` lines; i18n strings in de/en.
- **Why**: Consistency with `androidTerminal.ts`, `androidPrinter.ts`, `probeApiBase.ts`; testable with the same Vitest bridge-mock style already used (`stripeTerminalAvailability.test.ts`).

### 6. Labelling honesty

- **Choice**: Label the line as device/Tap-to-Pay readiness (e.g. `Tap to Pay: bereit` / `nicht unterstützt` / `Standort fehlt`), not "Stripe OK". In debug builds append a simulated hint.
- **Why**: Avoid implying an end-to-end payment guarantee we did not verify.

## Risks / Trade-offs

- [Risk] Location-permission race on first launch → status shows `location_missing` prematurely → Mitigation: run on Admin open (post-prompt); show a neutral "checking…" state while the async check resolves; offer a re-check by reopening Admin.
- [Risk] Moving/forcing `Terminal.init` earlier than first pay could surface init errors in Admin → Mitigation: init inside the check, catch and map to `error`; do not block Admin rendering; charge flow init path unchanged.
- [Risk] `supportsReadersOfType` requires location/bluetooth permission acceptance as part of init and may prompt → Mitigation: permissions are already requested at `MainActivity` startup; the check reuses granted permissions and only reports `location_missing` when absent.
- [Risk] Debug vs release divergence (simulated reader) → Mitigation: distinct `ready_simulated` code + UI hint so debug never masquerades as production-ready.
- [Trade-off] Device-only readiness can still be followed by a pay-time failure (org not onboarded, cloud down) → Accepted for this change; documented; cloud/org layer is a future extension.

## Migration Plan

1. Ship Android bridge additions (`getAppInfo`, `checkTapToPaySupport`) + `MainActivity` wiring; bump `VERSION` per release label as usual.
2. Ship Pi frontend utils + `AdminHubView` lines + i18n + tests.
3. No backend/OpenAPI deploy step. Rollback = hide the two Admin lines / remove bridge calls; native methods are additive and harmless if unused.

## Open Questions

1. New dedicated `AndroidApp` bridge vs. extending `AndroidTerminal` for `getAppInfo()`? **Default: small `AndroidApp` bridge** so version works when Terminal is unsupported.
2. Should the readiness line optionally fold in cloud reachability (`/v1/cloud/reachable`) to show a combined "can take cards now" state, or stay strictly device-only? **Default: device-only for this change**; cloud layer is a follow-up.
3. Do we also want the check to run once opportunistically at startup (cached) so Admin shows an instant result, with Admin-open as refresh? **Default: Admin-open only**, per request; revisit if the check feels slow.
