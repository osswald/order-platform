## Context

The Android waiter app (`android/…`) wraps the Pi PWA in a WebView with edge-to-edge layout. System bars stay visible; `AndroidInsets` pushes `--safe-*` CSS so POS screens clear the status/nav bars. Kitchen, pickup, and customer-display routes already use Vue `meta.fullscreen` (hide in-app chrome) but still show Android system UI.

Kitchen tablets are often dedicated displays. Chrome on `http://<pi-ip>/…` cannot install a true standalone PWA, so the practical path is the Vendiqo APK in immersive mode for those routes.

Admin **Küchenmonitor** builds absolute URLs with `window.location.origin`, which is `https://appassets.androidplatform.net` for the bundled WebView — useless for copy/share and awkward for `window.open`.

## Goals / Non-Goals

**Goals:**

- Hide status and navigation bars while on kitchen / pickup / register-display routes inside the Android app.
- Restore normal (edge-to-edge, bars visible) behavior when navigating back to hubs, order, pay, admin, etc.
- Let kitchen UI use the full WebView when immersive (insets ≈ 0).
- On Android, open kitchen monitors via in-app navigation; copy URLs using the configured Pi API base.
- Preserve existing Android safe-layout behavior for waiter/register POS.

**Non-Goals:**

- TLS / installable Chrome PWA over the venue LAN.
- True kiosk lockdown (screen pinning, device-owner, disable back) — document pinning as optional ops advice only.
- Changing kitchen ticket UX, polling, or print actions.
- Immersive mode on iOS / desktop browsers.
- Hiding bars on all `fullscreen` routes (order/pay stay non-immersive).

## Decisions

### 1. Route meta `immersive` (not reuse `fullscreen`)

- **Choice**: Add `meta.immersive: true` on `kitchen`, `pickup`, and `register-display` only.
- **Why**: `fullscreen` already means “no Pi shell chrome” for order/pay/kitchen; waiter POS must keep system bars and safe insets.
- **Alternative**: Infer immersive from path regex in native code — rejected (brittle, duplicates router knowledge).
- **Alternative**: Immersive for every `fullscreen` route — rejected (hurts order/pay usability and tap targets near edges).

### 2. JS bridge on `AndroidApp`: `setImmersiveMode(enabled: boolean)`

- **Choice**: Extend `AndroidAppBridge` with `@JavascriptInterface fun setImmersiveMode(enabled: Boolean)` that posts to the main thread and toggles `WindowInsetsControllerCompat` hide/show for `systemBars()`. Use sticky immersive behavior (`BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE`) so a swipe can briefly reveal bars without stranding the user.
- **Why**: PWA already owns routing; native owns window insets. Matches existing bridge style (`AndroidApp`, `AndroidInsets`).
- **Alternative**: Native `WebViewClient` URL sniffing — rejected (SPA hash/history and asset-loader URLs are messy).
- **No-op** when bridge absent (browser / non-Android).

### 3. PWA drives immersive from a small composable / App.vue watch

- **Choice**: Watch `route.meta.immersive` (and `isAndroidApp()`); call `AndroidApp.setImmersiveMode(true|false)`. On leave / unmount, always request `false`.
- **Why**: Single place; survives in-app back navigation.
- After toggle, re-apply insets to WebView (controller change may fire inset callbacks with zeros).

### 4. Insets while immersive

- **Choice**: When bars are hidden, inset listener reports ~0; CSS `--safe-*` become `0px` so kitchen header/content can use the full area (including under former status-bar region). Transient swipe-shown bars may briefly bump insets — acceptable.
- **Why**: Matches “true monitor” goal; kitchen header is not a critical gesture zone under a permanent status bar.
- **Alternative**: Keep painting under bars but reserve safe padding — rejected (defeats fullscreen).

### 5. Admin open + copy URLs on Android

- **Choice**:
  - `absoluteUrl(path)`: if `isAndroidApp()`, prefix with `getApiBase()` (Pi nginx origin, no trailing slash) instead of `window.location.origin`. Path remains router `href` (e.g. `/kitchen/grill?event=3`). Note: bundled asset start URL includes `/public/`; Pi nginx serves at `/` — copied URLs must be Pi paths without `/public`.
  - `openKitchen` / open display: if `isAndroidApp()`, `router.push({ name, params, query })` instead of `window.open`.
- **Why**: Fixes copy/share for other tablets/Chrome; in-app open triggers immersive without broken `appassets` tabs.
- **Alternative**: Always use Pi base even in browser — unnecessary; browser origin is already correct when served from nginx.

### 6. Scope: kitchen + pickup + register-display

- Same wall-tablet pattern; one meta flag and one bridge path. No extra UI unless needed later.

## Risks / Trade-offs

- **[Risk] User cannot reach system nav / status without knowing swipe-from-edge** → Mitigation: sticky transient bars by swipe; document; back gesture still leaves route via WebView back / in-app controls where present.
- **[Risk] Gesture conflicts on some OEMs** → Mitigation: keep immersive limited to display routes; QA on a real tablet.
- **[Risk] `getApiBase()` points at `:8001` while PWA is on `:80`** → Mitigation: existing Admin default is nginx `http://192.168.192.10` without port; document that copy URL uses the saved Pi-API base (same as API). If someone set `:8001`, kitchen HTML may 404 — same class of misconfig as today for API.
- **[Risk] `window.open` still used on non-Android** → Acceptable for desktop admin.
- **[Trade-off]** Immersive does not equal MDM kiosk; operators may still want screen pinning.

## Migration Plan

1. Ship Android + Pi frontend together (bridge + callers). Older APK without `setImmersiveMode`: PWA no-ops; bars stay (no crash).
2. No DB/schema migration.
3. Rollback: revert APK / frontend; behavior returns to edge-to-edge with bars.

## Open Questions

- None blocking. Optional follow-up: deep-link intent extra to cold-start directly into a kitchen URL (out of scope unless requested).
