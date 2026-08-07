## Why

The Android waiter app should reward a named insider joke: when waiter **Edi** logs in, a brief dial-up modem “handshake” overlay makes the device feel like it is connecting — without blocking or breaking normal login if audio fails.

## What Changes

- On successful waiter login in the Android app only, if the waiter display name matches `edi` (case-insensitive), show a full-screen overlay with a spinner and the text `Connecting...`.
- Raise media volume to 75%, play the first **15 seconds** of the public-domain dial-up modem clip ([Dial up modem noises.ogg](https://commons.wikimedia.org/wiki/File:Dial_up_modem_noises.ogg)), then restore the previous volume and navigate to the waiter hub.
- On any playback failure (missing asset, prepare/play error, or similar), fail soft: restore volume if changed, dismiss the overlay, and still enter the hub so login never gets stuck.
- Non-Android clients (browser / Pi PWA without the native bridge) keep today’s login → hub path with no overlay or volume changes.

## Capabilities

### New Capabilities

- `android-edi-modem-login`: Android-only waiter login easter egg (overlay, volume, modem playback, soft-fail).

### Modified Capabilities

- (none)

## Impact

- **Android native:** extend `AndroidApp` (or a small audio bridge) with volume save/set/restore and modem playback; ship a trimmed 15s clip under `res/raw/` plus a short attribution note.
- **Pi frontend:** gate the egg in waiter login (`LoginView` / related helpers) via `isAndroidApp()` + name match; UI overlay component.
- **Tests:** Kotlin bridge unit tests; Vue/Vitest coverage for trigger, non-Android skip, and soft-fail path.
- **No** backend/API/schema changes; no cloud frontend impact.
