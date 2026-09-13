## ADDED Requirements

### Requirement: Display-sized screensaver HTTP

The Pi customer-display HTTP endpoint for a screensaver hash SHALL return a JPEG whose longest edge is at most 1920 pixels. The content-addressed local store MUST keep the original uploaded bytes unchanged. URL identity SHALL remain the original content hash.

#### Scenario: Large original is downscaled for playback

- **WHEN** the local store holds a screensaver image whose longest edge exceeds 1920 pixels
- **AND** the customer display requests that image by hash
- **THEN** the HTTP response body is a JPEG with longest edge at most 1920 pixels

#### Scenario: Store retains original

- **WHEN** the Pi has downloaded a screensaver original by content hash
- **THEN** a later display request does not replace or rewrite the stored original file

### Requirement: WebView-safe idle gallery load

When the idle customer display loads organisation gallery images, it SHALL obtain image bytes through the Pi API (`fetch`) and present them as blob object URLs. It MUST NOT rely on the browser decoding raw camera originals via `<img src>` pointing at Pi HTTP. Failed individual images MUST be skipped; if none load, the display SHALL show the welcome fallback.

#### Scenario: Idle gallery uses blob URLs

- **WHEN** display state is idle and at least one screensaver image is available locally
- **THEN** the customer display renders gallery frames from `blob:` URLs created from fetched image bytes

#### Scenario: Partial fetch failure falls back

- **WHEN** the gallery list is non-empty but every image fetch fails
- **THEN** the customer display shows `Herzlich Willkommen`

### Requirement: Android bundled WebView must not intercept Pi HTTP

The Android Waiter WebView asset loader SHALL intercept only requests whose host is the bundled app origin (`appassets.androidplatform.net`). Requests to the venue Pi (API and screensaver images) MUST reach the network.

#### Scenario: Pi screensaver URL is not asset-loaded

- **WHEN** the Waiter WebView requests a screensaver image from the configured Pi HTTP base
- **THEN** the request is not answered by the bundled asset loader
