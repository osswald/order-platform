## 1. Tests first (Pi frontend)

- [x] 1.1 Add Vitest coverage for absolute URL helper: on Android (`isAndroidApp`), kitchen/display absolute URLs use `getApiBase()` host, not `window.location.origin` / `appassets`
- [x] 1.2 Add Vitest coverage for `openKitchen` (and display open if shared): on Android uses `router.push` with event query; non-Android may still use `window.open`
- [x] 1.3 Add Vitest coverage for immersive driver: when `route.meta.immersive` and Android bridge present, calls `setImmersiveMode(true)`; leaving route calls `false`; missing bridge is a no-op
- [x] 1.4 Extend router meta / guard tests so kitchen, pickup, and register-display declare `immersive: true` while order/pay remain non-immersive

## 2. Android immersive bridge

- [x] 2.1 Add JVM unit test(s) for immersive toggle helper / bridge contract where practical (e.g. enabled flag plumbing); document manual QA for WindowInsetsController if untestable in JVM
- [x] 2.2 Implement `AndroidAppBridge.setImmersiveMode(enabled: Boolean)` (or Activity-held controller) using `WindowInsetsControllerCompat` hide/show system bars with sticky transient swipe behavior on the UI thread
- [x] 2.3 Wire controller from `MainActivity` into the bridge; ensure inset listener still updates `--safe-*` when bars hide/show

## 3. Pi frontend immersive + Admin URLs

- [x] 3.1 Add `immersive?: boolean` to router meta types; set `immersive: true` on kitchen, pickup, and register-display routes
- [x] 3.2 Implement composable (or App.vue watch) that syncs `meta.immersive` → `AndroidApp.setImmersiveMode` when `isAndroidApp()`
- [x] 3.3 Update `Window` / `AndroidApp` typings for `setImmersiveMode`
- [x] 3.4 Fix `useAdminOperations` / `useRegisterDisplay` absolute URL + open helpers for Android (Pi base + in-app navigation)
- [x] 3.5 Confirm kitchen CSS does not force a permanent status-bar gap when `--safe-top` is 0 in immersive mode (adjust only if a regression appears)

## 4. Docs and verification

- [x] 4.1 Document kitchen-tablet setup in `android/README.md` (open monitor in app → immersive; optional screen pinning; copy URL uses Pi-API base)
- [x] 4.2 Run Pi frontend tests and Android unit tests; run `./scripts/lint.sh` for touched areas
- [ ] 4.3 Manual QA on a tablet: Admin → Monitor öffnen → bars hidden; navigate back → bars restored; order screen still clears status bar; copied kitchen URL uses Pi host
