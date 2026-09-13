## Context

See proposal.md — Why. The organisation gallery already syncs originals to the Pi (content-addressed store, manifest in the edge bundle). `GET /v1/screensaver/{sha256}` previously returned those originals. The Android Waiter UI is a HTTPS WebView (`appassets.androidplatform.net`) talking to LAN HTTP Pi APIs. Camera JPEGs in this venue are ~6000×4000 / 7–8 MB (under the 10 MB upload cap, no cloud resize).

## Goals / Non-Goals

**Goals:**

- Customer-display playback that Android WebView and Elo kiosk browsers can decode.
- Keep download-once originals on the Pi (no re-upload, no cloud transcode).
- Stop the Android asset loader from 404ing Pi HTTP.

**Non-Goals:**

- Changing upload size limits or adding cloud-side resize.
- Event-level galleries or reorder UI.
- Changing greyscale (still a CSS/display filter on unchanged stored bytes).
- Live Pi OTA / APK sideload as part of this change (deploy separately).

## Decisions

### 1. Downscale on display GET, not in the store

- **Choice:** `jpeg_bytes_for_display` (Pillow, EXIF transpose, max edge 1920, JPEG quality 82) on `GET /v1/screensaver/{sha256}` only.
- **Why:** Hash identity and sync GC stay original-based; playback size is a display concern.
- **Alternatives:** Resize on cloud upload — extra pipeline, existing files stay huge until re-upload. Resize into a second store file — more GC surface. Serve originals and hope the WebView copes — already failed in the field.

### 2. Fetch + blob URLs on the display page

- **Choice:** `loadScreensaverObjectUrls` fetches list then each image, `URL.createObjectURL`; revoke on reload/unmount.
- **Why:** Avoids `<img src="http://pi/...">` mixed-content / huge-decode failures from the HTTPS WebView origin.
- **Alternatives:** Proxy images through `appassets` — wrong host and CORS. Native Android image view — splits POS/display stack.

### 3. Intercept only the bundled asset host

- **Choice:** `shouldInterceptRequest` returns `null` unless `host == appassets.androidplatform.net`.
- **Why:** `WebViewAssetLoader` on every URL can return a miss for Pi HTTP and look like a broken gallery.
- **Alternatives:** Keep intercepting all URLs and special-case `http` — host allow-list is simpler.

## Risks / Trade-offs

- **[Risk] First idle frame waits on sequential fetches** → Mitigation: images are few (max 10) and now small JPEGs; skip per-hash failures.
- **[Risk] CPU on Pi per GET** → Mitigation: decode/resize is cheap vs 8 MB originals on a tablet; cache later if needed.
- **[Trade-off] Display HTTP is always JPEG** → PNG uploads still play; store mime in the manifest is informational for list only.
- **[Risk] Pi OTA without new APK** → Downscale still helps Elo Firefox; blob + intercept need the Waiter APK.

## Migration Plan

1. Land Pi backend + frontend (OTA): kiosk browsers get smaller JPEGs even with `<img>` if an old PWA remains.
2. Ship Waiter APK: blob loading + intercept host check.
3. Rollback: revert display GET to originals and display to `<img src>`; gallery sync unchanged.

## Open Questions

None — field failure mode (Android current APK, originals present on Pi, blank idle) is addressed by the three decisions above.
