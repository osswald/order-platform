## Context

Stripe Tap to Pay runs in the Android waiter WebView via `window.AndroidTerminal.collectPayment(...)`. The Pi PWA payment picker enables **Karte** when:

1. The Android app / `AndroidTerminal` bridge is present
2. Cloud is reachable (`GET /v1/cloud/reachable`)

There is no check of NFC / OS / GMS / hardware keystore fitness. Unsupported devices only fail inside `discoverReaders` / `connectReader` during payment. Stripe documents `Terminal.supportsReadersOfType(DeviceType.TAP_TO_PAY, …)` as the runtime API for this (~10ms after Terminal init). The bridge already has an unused `isAvailable()` that only reports `Terminal.isInitialized()`, not device support.

## Goals / Non-Goals

**Goals:**

- Detect Tap to Pay support on the current Android device using the Stripe Terminal SDK.
- Expose that result to the Pi PWA through the existing JS bridge.
- Disable **Karte** with a clear German hint when the device is unsupported.
- Keep existing Android-app and cloud-reachability gates; compose device support as an additional gate.
- Cover the new availability logic with Vitest (and document Android manual checks).

**Non-Goals:**

- Changing cloud/Pi Terminal APIs, PaymentIntent shape, or Connect onboarding.
- Supporting external Bluetooth/USB Stripe readers.
- Guaranteeing every Stripe soft criterion (rooted, Developer options, 12‑month security patch) — those may still fail at discover/connect.
- iOS Tap to Pay.
- Blocking install of the Play app on unsupported devices (`uses-feature` NFC stays `required=false`).

## Decisions

### 1. Use Stripe `supportsReadersOfType`, not a home-grown NFC check

**Choice:** After Terminal init, call `Terminal.getInstance().supportsReadersOfType(DeviceType.TAP_TO_PAY, DiscoveryConfiguration.TapToPayDiscoveryConfiguration(isSimulated = BuildConfig.DEBUG))` and map `ReaderSupportResult` to a boolean (+ optional error message).

**Alternatives considered:**

- `PackageManager.FEATURE_NFC` only — incomplete vs Stripe’s OS/keystore/GMS rules; would false-positive.
- Rely on `discoverReaders` at picker time — slower, needs connection token / more setup; worse for UI gating.
- Static allow-list of models — unmaintainable.

### 2. New bridge method `supportsTapToPay()` (do not overload `isAvailable`)

**Choice:** Add `@JavascriptInterface fun supportsTapToPay(): String` returning JSON:

```json
{ "ok": true, "supported": true }
```

or

```json
{ "ok": true, "supported": false, "error": "…" }
```

or on hard failure to evaluate:

```json
{ "ok": false, "error": "…" }
```

Leave existing `isAvailable()` unchanged (initialized-only) so semantics stay clear.

**Alternatives considered:**

- Repurpose `isAvailable()` — confusing; already means “SDK initialized”.
- Async callback into JS — more WebView plumbing; sync string return matches `collectPayment` / printer bridges.

### 3. When to initialize Terminal for the check

**Choice:** Lazily initialize Terminal inside `supportsTapToPay()` the same way as `collectPayment` (UI-thread `Terminal.init` + existing token provider stub). Require location permission for a definitive check; if location is missing, return `{ ok: false, error: "…" }` so the PWA can show a location-oriented hint rather than claiming the device is unsupported.

**Alternatives considered:**

- Init Terminal at app startup — earlier permission prompt; heavier cold start.
- Skip init and only check NFC feature — inaccurate (decision 1).

### 4. PWA gating composition and hint priority

**Choice:** Extend `stripeTerminalPickerEntry` / `stripeTerminalDisabledHint` to:

1. Not Android → «Nur in der Android-App verfügbar.»
2. Cloud unreachable → «Cloud-Verbindung erforderlich.»
3. Location / check failure that blocks evaluation → location or generic readiness hint (reuse or add «Standortberechtigung für Kartenzahlung erforderlich.»)
4. `supported === false` → «Gerät unterstützt keine Kartenzahlung (Tap to Pay).»

If the bridge method is **missing** (older APK), treat device support as **unknown and allow** (current behavior) so venues are not broken until they update the app.

Cache the support result for the session (module-level, similar to cloud reachability cache, longer TTL or until process restart is fine — hardware does not change mid-shift).

**Alternatives considered:**

- Fail closed when method missing — would disable Karte on every un-updated APK.
- Fail open when `supported === false` — defeats the feature.

### 5. Debug / simulated builds

**Choice:** Pass `isSimulated = BuildConfig.DEBUG` into the discovery configuration used for `supportsReadersOfType`, matching collect-time discovery. Debug APKs on emulators without NFC can still report supported under simulation.

**Alternatives considered:**

- Always check non-simulated — breaks local emulator QA of the picker path.

### 6. Docs and tests

**Choice:** Update `docs/stripe-connect-terminal.md` payment-type availability section; Vitest for hint priority and picker entry with mocked bridge; no new backend tests. Manual Android checklist for a supported phone vs unsupported (or NFC-off) device.

## Risks / Trade-offs

- **[Risk] Soft Stripe criteria still fail at collect** → Document that the check is best-effort; keep collect-time errors user-visible.
- **[Risk] Location permission timing** → Distinct hint for missing location; `MainActivity` already requests terminal permissions on launch.
- **[Risk] Older APKs without `supportsTapToPay`** → Fail open for missing method (decision 4).
- **[Risk] Terminal init cost on first picker open** → Cache result; Stripe claims ~10ms for the support call after init.
- **[Trade-off] German-only waiter hints** — matches existing picker copy; no i18n expansion in this change.

## Migration Plan

- Ship Android bridge + Pi frontend together in the next waiter app build (bundled assets). Older APKs keep prior enablement rules.
- No data migration; rollback by reverting the bridge method usage in the PWA (or full revert).

## Open Questions

- None blocking. Optional follow-up: surface support status on an Admin / device diagnostics screen (out of scope unless trivial once the bridge exists).
