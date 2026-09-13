## Why

Idle customer-display gallery images sync to the Pi and play in a LAN browser, but the Android Waiter WebView cannot load typical camera originals (multi-megabyte, thousands of pixels). Operators on a tablet therefore see a blank idle screen instead of the organisation gallery.

## What Changes

- Pi `GET /v1/screensaver/{sha256}` serves a **display-sized JPEG** (max edge 1920px) while the content-addressed store keeps the original bytes.
- The Pi customer display loads gallery frames with **`fetch` + `blob:` object URLs**, not raw `http://` `<img src>` pointing at the Pi (Android mixed-content / huge-decode path).
- Android `WebViewClient.shouldInterceptRequest` intercepts **only** `appassets.androidplatform.net` so Pi HTTP image/API requests are not swallowed by the asset loader.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `customer-display-screensaver`: Idle playback MUST work on the Android Waiter WebView; Pi display HTTP MUST downscale for kiosk/WebView decode; originals remain in the local hash store.

## Impact

- **Pi backend:** `screensaver_display.py`, `GET /v1/screensaver/{sha256}` response body (still keyed by original sha256).
- **Pi frontend:** `RegisterDisplayView` idle gallery loading (`screensaverDisplay.ts`).
- **Android app:** `MainActivity` request intercept host check (APK rebuild required for blob loading + intercept fix).
- **Cloud / bundle / sync:** unchanged (manifest + original download-once).
- **Deploy:** Pi OTA for downscale; new Waiter APK for blob URLs and intercept fix.
