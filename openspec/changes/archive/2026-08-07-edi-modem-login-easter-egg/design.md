## Context

See proposal.md — Why. The Android APK is a WebView shell around the Pi PWA (`MainActivity` + `JavascriptInterface` bridges such as `AndroidApp`). Waiter login lives in `pi/frontend` `LoginView`: after PIN validation it `setWaiter`s and `router.replace`s to the hub. There is no audio/volume bridge today.

## Goals / Non-Goals

**Goals:**

- Trigger only on Android after a successful waiter login when the waiter name equals `edi` (trim + case-insensitive).
- Coordinated overlay + volume bump + 15s modem playback + volume restore + hub navigation.
- Soft-fail so login always completes to the hub.

**Non-Goals:**

- Triggering on hub device-switch or register login.
- Changing volume or playing audio outside Android.
- Shipping the clip in the Pi browser PWA for non-Android clients.
- User-facing settings to enable/disable the egg.
- Exact acoustic fidelity beyond the trimmed Commons sample.

## Decisions

### 1. Native playback + volume in one bridge method

**Choice:** Extend `AndroidApp` with a single async-friendly entry such as `playModemHandshake()` that: (1) reads current `STREAM_MUSIC` volume, (2) sets ~75% of max, (3) plays `R.raw.modem56k` (first 15s of the Commons OGG, committed as a truncated asset), (4) on completion or error restores the saved volume, (5) notifies the WebView via a JS callback or a Promise-shaped bridge pattern already used in the app if one exists; otherwise return JSON sync start + `evaluateJavascript` completion callback.

**Why:** Volume control requires `AudioManager`; keeping playback next to volume avoids race conditions between HTML5 audio and native volume. Overlay stays in Vue.

**Alternatives considered:**

- HTML5 `<audio>` in the PWA + separate volume APIs — works, but the sound asset would ship in every Pi frontend build and completion/volume ordering is messier across WebView.
- Always restore to 0% — rejected; restore previous volume instead.

### 2. Completion signalling to the PWA

**Choice:** Prefer a fire-and-forget native method that accepts a callback name, or posts a custom `window` event when done/failed; the PWA awaits that before dismissing overlay and navigating. Document the contract in `env.d.ts`.

**Why:** `@JavascriptInterface` methods typically return immediately; MediaPlayer is async. Matching existing immersive bridge style (sync void) plus a single completion event keeps the surface small.

### 3. Soft-fail contract

**Choice:** Any of: missing raw resource, `MediaPlayer` prepare/start failure, activity destroyed mid-play → restore volume if we changed it, signal completion with `ok: false` (or equivalent), PWA dismisses overlay and navigates to hub. Silent/DND modes that merely quiet audio still count as success once playback “ends” (or after a short max timeout ~20s if no callback).

**Why:** Login must never block on an easter egg.

### 4. Asset & attribution

**Choice:** Commit a ~15s Ogg (or AAC/MP3 if tooling prefers) under `android/app/src/main/res/raw/`, derived from [Dial up modem noises.ogg](https://commons.wikimedia.org/wiki/File:Dial_up_modem_noises.ogg) (William Termini, public domain). Add a brief `NOTICE`/`ATTRIBUTION` line (source URL, author, PD, “first 15 seconds”).

**Why:** Public domain allows redistribution; trimming at build/commit time avoids runtime seeking complexity.

### 5. UI placement

**Choice:** Full-viewport Vue overlay shown from login flow (or a tiny composable) before hub navigation; text exactly `Connecting...` plus an existing spinner pattern if one exists in the Pi UI.

**Why:** Keeps branding/UX in the PWA; native only handles audio/volume.

## Risks / Trade-offs

- **[Risk] Hardware mute / DND** → User hears little or nothing; still wait for natural end or timeout, then hub. Soft-fail covers hard errors.
- **[Risk] Volume fight with other apps** → We only touch `STREAM_MUSIC` and restore; brief 15s window.
- **[Risk] Activity destroy mid-egg** → Release `MediaPlayer` in cleanup; restore volume in `onDestroy`/error path if still elevated.
- **[Trade-off] ~15s delayed hub** → Acceptable for a rare name match; non-matching waiters unchanged.

## Migration Plan

- Ship in a normal Android + Pi frontend release; no data migration.
- Rollback: remove trigger / bridge call; unused raw asset is harmless if left temporarily.

## Open Questions

None — soft-fail, restore volume, Android-only, and Commons 15s clip are decided.
