## Why

Venue teams want to run the kitchen **Bestellungen** monitor on an Android tablet. Chrome cannot hide its chrome over the Pi’s plain HTTP LAN URL, and today’s Vendiqo Android app keeps the status and navigation bars visible (edge-to-edge with safe insets). That wastes screen space and looks wrong for a dedicated kitchen display. Admin also shows unusable `appassets.androidplatform.net` monitor URLs when opened inside the app.

## What Changes

- Enter **immersive fullscreen** (hide Android status and navigation bars) when the WebView is on kitchen monitor routes; restore normal system bars when leaving those routes.
- Apply the same immersive behavior to other fixed **ops display** routes that are meant for wall/tablet use: customer pickup and register customer display (same product need).
- Keep waiter/register POS screens **non-immersive** (status/nav bars stay; existing safe-inset layout unchanged).
- Expose a small JS bridge so the Pi PWA can request immersive on/off; drive it from the Vue router based on route meta.
- When immersive, treat system-bar insets as zero so the kitchen UI can use the full WebView.
- Fix Admin **Küchenmonitor** (and sibling display URL helpers) on Android so **Monitor öffnen** navigates in-app and **URL kopieren** uses the configured Pi HTTP base (`getApiBase()`), not `appassets.androidplatform.net`.

## Capabilities

### New Capabilities

- `android-immersive-display`: Immersive system UI for kitchen / pickup / customer-display routes inside the Android WebView wrapper, including bridge contract and Admin open/copy URL behavior on Android.

### Modified Capabilities

- `pi-android-safe-layout`: Clarify that immersive display routes intentionally drop system-bar insets (safe-* ≈ 0) while other Android fullscreen POS screens keep clearing status/nav bars as today.

## Impact

- **Android**: `MainActivity` (WindowInsetsController / immersive), extend `AndroidApp` (or dedicated) JS bridge; unit tests where practical.
- **Pi frontend**: router meta (e.g. `immersive`), composable watching route → bridge; kitchen/pickup/display already `fullscreen: true`; Admin operations URL builders (`useAdminOperations`, register display helper); TypeScript `Window` typings; Vitest coverage.
- **Docs**: short note in `android/README.md` and/or `pi/README.md` for kitchen tablets.
- No cloud/backend API changes. No change to Chrome/PWA installability over HTTP.
