## Context

The Waiter Android app (`android/`) wraps the Pi PWA in a WebView. It already uses `enableEdgeToEdge()`, injects system-bar/IME insets via `AndroidInsetsBridge`, and integrates Stripe Terminal Tap to Pay through `StripeTerminalBridge` (`stripeterminal-core` + `stripeterminal-taptopay` **5.5.1**). Build config pins `compileSdk` / `targetSdk` **35**, `minSdk` **33**.

Google Play requires target API **36** for new apps and updates from **31 August 2026** (extension available to 1 November 2026). Play Console already warns; existing target-35 builds remain distributable until an update is submitted.

AGP **9.2.1** / Gradle **9.4.1** already support compiling against API 36. No toolchain bump is required for the SDK level change itself.

## Goals / Non-Goals

**Goals:**

- Ship a Play-compliant release build with `targetSdk` / `compileSdk` 36
- Move Stripe Terminal to **5.7.0** in the same change
- Adopt `LocaleConfig` on `Terminal.init` so Tap to Pay attestation errors are not stuck on English-only defaults
- Document the new SDK levels and keep README accurate

**Non-Goals:**

- Changing `minSdk`
- Adopting Stripe preview features (surcharging, donations, etc.)
- Refactoring payment flow to `processPaymentIntent` / `easyConnect` (optional SDK 5.x APIs; leave for a later change)
- Pi frontend feature work (IME sheets remain a separate in-flight change)
- Requesting Play Console extension (unnecessary if we ship before 31 Aug)

## Decisions

### 1. Single change: API 36 + Terminal 5.7.0

- **Choice:** One PR / one Play upload covering both bumps.
- **Why:** Next upload after Aug 31 must be API 36 anyway; Terminal 5.7.0 includes Tap to Pay connection and orientation fixes worth having on the same binary. Two uploads before the deadline waste review cycles.
- **Alternatives:** API-only bump first (smaller blast radius, but a second release soon); Terminal-only bump now (does not clear the Play warning).

### 2. Jump 5.5.1 → 5.7.0 (skip publishing on 5.6.0)

- **Choice:** Set `stripeTerminalVersion = "5.7.0"` for both Maven artifacts.
- **Why:** 5.6.0 had an offline DB migration data-loss bug when upgrading from ≤4.1.0; fixed in 5.7.0. Even if we never used offline mode, landing on current avoids a known-bad intermediate.
- **Alternatives:** Stay on 5.5.1 with only targetSdk 36 (misses Tap to Pay fixes; unknown 36 validation); go to 5.6.0 (unnecessary risk).

### 3. `LocaleConfig.CardLanguagePreferenceIfAvailable` on init

- **Choice:** Replace the deprecated `Terminal.init(..., offlineListener = null)` call with the overload that takes `LocaleConfig`, using `CardLanguagePreferenceIfAvailable`.
- **Why:** 5.6.0+ Tap to Pay attestation messages default to `en-US` unless locale is configured; CH venues run a German UI. Card-language preference matches prior “follow locale when available” behavior without hardcoding `de-CH`.
- **Alternatives:** `HardcodedLocale(Locale.GERMAN)` (simpler but ignores device/card preference); leave deprecated overload (compiles today, English attestation strings, will break later).

### 4. No large-screen orientation opt-out

- **Choice:** Do not set `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY`. Rely on existing unlocked orientation + WebView POS layout.
- **Why:** Manifest has no `screenOrientation` lock; primary devices are tablets (`sw600dp+`) where API 36 ignores locks anyway. Temporary opt-out disappears in a future API level.
- **Alternatives:** Opt out for breathing room (delays adaptive work; still need to remove later).

### 5. Edge-to-edge: no new native inset work

- **Choice:** Keep current `enableEdgeToEdge()` + CSS inset bridge; smoke-test after bump.
- **Why:** Target 36 removes the edge-to-edge opt-out; we already opted in and own the web content. Residual risk is IME/sheet padding (covered by separate `pi-android-text-input-sheets` work).

### 6. Version pin stays in Gradle only

- **Choice:** Specs require “current Terminal init with locale config” and “target API ≥ 36”; exact `5.7.0` lives in design/tasks/Gradle, not as a forever-pinned SHALL in living specs.
- **Why:** Pinning patch versions in specs goes stale; Play target level and init contract are the durable requirements.

## Risks / Trade-offs

- **[Risk] Stripe Terminal 5.7.0 regresses Tap to Pay on venue devices** → Mitigate with manual QA on a supported tablet (discover, connect, collect test-mode payment); keep `supportsTapToPay` unit paths unchanged.
- **[Risk] Compiling against API 36 pulls newer AndroidX / AAR metadata that conflict with AGP** → Unlikely on AGP 9.2.1; if build fails, bump the conflicting AndroidX dep only as needed.
- **[Risk] Large-screen multi-window / rotation breaks POS layout** → Smoke-test rotate and split-screen on 7"/10" tablet; fix only if broken (CSS under `html.android-app`).
- **[Risk] LocaleConfig changes error-string language in tests or support scripts** → Prefer asserting error codes / `ok` flags over English substrings in any new tests.
- **[Trade-off] Combining SDK + targetSdk increases blast radius** → Accepted; deadline and Tap to Pay fixes favor one release.

## Migration Plan

1. Feature branch from `main`; implement Gradle + bridge + docs.
2. Local: `./gradlew assembleDebug` (and unit tests under `android/app/src/test`).
3. Device QA: Tap to Pay + insets + tablet rotate.
4. PR → merge → existing Android release workflow `bundleRelease` / Play upload (internal first).
5. Confirm Play Console target API warning clears on the new version.
6. Rollback: republish previous AAB if critical Tap to Pay failure (Play still allows existing target-35 artifact until next update; after Aug 31, rollback builds must themselves target 36).

## Open Questions

- None blocking. Confirm during apply whether CI Android SDK image already includes `platforms;android-36` (install if the workflow fails on missing platform).
