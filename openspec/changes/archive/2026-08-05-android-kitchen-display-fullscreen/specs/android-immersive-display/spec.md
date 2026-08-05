## ADDED Requirements

### Requirement: Immersive system UI on Android display routes

When the Pi frontend runs inside the Vendiqo Android WebView and the active route has `meta.immersive` true (kitchen monitor, pickup screen, or register customer display), the Android app SHALL hide the status bar and navigation bar (immersive / sticky transient bars). When the active route does not have `meta.immersive`, the app SHALL show system bars again with the existing edge-to-edge inset behavior.

#### Scenario: Enter kitchen monitor hides system bars

- **WHEN** the user navigates to a kitchen monitor route inside the Android app
- **THEN** the Android status bar and navigation bar are hidden
- **AND** the kitchen Bestellungen / Produkte UI occupies the WebView without permanent system-bar chrome

#### Scenario: Leave kitchen restores system bars

- **WHEN** the user navigates from a kitchen monitor route to a non-immersive route (e.g. Events or Admin) inside the Android app
- **THEN** the status bar and navigation bar are visible again

#### Scenario: Non-Android no-op

- **WHEN** the same immersive route is opened in a normal browser (no Android immersive bridge)
- **THEN** the page loads without error and does not depend on native immersive APIs

### Requirement: Immersive bridge contract

The Android app SHALL expose a JavaScript interface method that the Pi PWA can call to enable or disable immersive mode. The call MUST be safe to invoke repeatedly and MUST run window inset changes on the Android UI thread.

#### Scenario: PWA requests immersive on

- **WHEN** the Pi frontend calls the immersive bridge with enabled = true on Android
- **THEN** system bars are hidden (sticky transient reveal by edge swipe is allowed)

#### Scenario: PWA requests immersive off

- **WHEN** the Pi frontend calls the immersive bridge with enabled = false on Android
- **THEN** system bars are shown

### Requirement: Immersive routes use full WebView without system-bar padding

While immersive mode is active on Android, system-bar safe-area CSS variables (`--safe-top`, `--safe-bottom`, and horizontal counterparts from the insets bridge) SHALL reflect the hidden bars (effectively zero inset for system bars) so display UIs are not double-padded for bars that are not visible.

#### Scenario: Kitchen header uses top of WebView when immersive

- **WHEN** the kitchen monitor is shown in immersive mode on Android
- **THEN** the kitchen header is not permanently offset by a status-bar-sized `--safe-top` gap

### Requirement: Android Admin opens kitchen in-app

On Android, opening a kitchen monitor from Admin Operations SHALL navigate inside the same WebView (router navigation) rather than relying on `window.open` with the bundled asset origin.

#### Scenario: Monitor öffnen on Android

- **WHEN** an operator taps **Monitor öffnen** for a kitchen station in the Android app
- **THEN** the kitchen monitor for that slug and selected operations event is shown in the same WebView
- **AND** immersive mode activates for that route

### Requirement: Android Admin copies Pi-reachable kitchen URLs

On Android, kitchen (and the same absolute-URL helpers used for customer display) copy/share strings SHALL use the configured Pi API base origin (`getApiBase()`), not `window.location.origin` when that origin is the WebView asset loader host.

#### Scenario: URL kopieren on Android

- **WHEN** an operator copies a kitchen monitor URL inside the Android app
- **THEN** the clipboard text starts with the configured Pi HTTP(S) base (e.g. `http://192.168.192.10`)
- **AND** includes `/kitchen/<slug>` and the `event` query parameter
- **AND** does not use `appassets.androidplatform.net` as the host
