# customer-display-screensaver Specification

## Purpose
Lets organisations brand the idle customer display with a synced image gallery that downloads once to the Pi and is cleared when gallery membership or the renting organisation changes.
## Requirements
### Requirement: Organisation screensaver gallery

Authorised organisation managers SHALL upload and delete screensaver images for their organisation. The gallery MUST contain at most 10 images. Image display order is unspecified (no reorder UI required). Supported types MUST include common web image formats (at least JPEG and PNG). Each image MUST respect a documented maximum byte size.

#### Scenario: Upload within limit

- **WHEN** an organisation has fewer than 10 screensaver images and uploads a valid image under the size limit
- **THEN** the image is stored and appears in the organisation gallery

#### Scenario: Reject eleventh image

- **WHEN** an organisation already has 10 screensaver images and attempts another upload
- **THEN** the upload is rejected

### Requirement: Edge bundle carries manifest only

The edge bundle for a paired Pi SHALL include a screensaver **manifest** (content hashes and mime types) for the appliance’s organisation. Image binary bytes MUST NOT be embedded in the catalogue bundle body. Manifest order is not significant.

#### Scenario: Bundle lists hashes without payloads

- **WHEN** the Pi pulls a bundle for an organisation with screensaver images
- **THEN** the bundle includes content hashes for those images and does not include the raw image bytes in the bundle JSON

### Requirement: Download once by content hash

During sync, for each hash in the organisation screensaver manifest, the Pi SHALL download the image from the cloud only if that hash is not already present in the local screensaver store. If the file already exists for that hash, the Pi MUST NOT transfer it again.

#### Scenario: Existing hash skipped

- **WHEN** the Pi syncs and a manifest hash already exists in the local store
- **THEN** no download is performed for that hash

#### Scenario: Missing hash downloaded

- **WHEN** the Pi syncs and a manifest hash is absent from the local store
- **THEN** the Pi downloads that image once and stores it under that hash

### Requirement: Delete local files removed from gallery

When a hash disappears from the organisation screensaver manifest, the Pi SHALL delete the corresponding local file on the next sync that applies that manifest.

#### Scenario: Removed image deleted locally

- **WHEN** an organisation deletes a screensaver image and the Pi later syncs the updated manifest
- **THEN** the local file for that image’s content hash is deleted

### Requirement: Wipe store on organisation or appliance change and unpair

When the paired organisation or appliance identity changes on bundle reconcile, or when the Pi is unpaired, the Pi SHALL delete all locally stored screensaver images for the previous tenant. After an organisation change, only the new organisation’s manifest images MAY be downloaded.

#### Scenario: Rented to different organisation

- **WHEN** a sync updates the bundle `organisation_id` to a different organisation
- **THEN** all previously stored screensaver image files are deleted from the Pi

#### Scenario: Unpair wipes screensaver store

- **WHEN** the Pi is unpaired
- **THEN** all locally stored screensaver image files are deleted

### Requirement: Idle customer display plays the gallery

When the customer display state is idle and the Pi has one or more screensaver images for the current organisation, the display SHALL show those images (rotating when more than one; sequence order is unspecified). When no screensaver images are available, the display SHALL show the existing welcome fallback (`Herzlich Willkommen`). Any non-idle display state MUST leave the screensaver immediately.

#### Scenario: Idle with gallery

- **WHEN** display state is idle and at least one screensaver image is available locally
- **THEN** the customer display shows gallery image(s) rather than only the welcome text

#### Scenario: Idle without gallery

- **WHEN** display state is idle and no screensaver images are available
- **THEN** the customer display shows `Herzlich Willkommen`

#### Scenario: Order activity ends screensaver

- **WHEN** display state changes from idle to ordering (or another non-idle state)
- **THEN** the screensaver is no longer shown

### Requirement: Organisation greyscale playback

Authorised organisation managers SHALL be able to enable greyscale playback for the organisation screensaver. When enabled, the idle customer display SHALL show gallery images in greyscale. Stored image bytes MUST remain unchanged (playback is a display filter). Cloud gallery previews SHALL use the same greyscale treatment so managers see what guests see. When the setting is off, images SHALL display in their original colour. The edge bundle SHALL include this flag; a missing flag MUST be treated as off.

#### Scenario: Greyscale on

- **WHEN** the organisation has screensaver greyscale enabled
- **AND** the idle customer display shows a gallery image
- **THEN** that image is shown in greyscale

#### Scenario: Greyscale off (default)

- **WHEN** the organisation has not enabled screensaver greyscale
- **THEN** idle gallery images are shown in original colour


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
