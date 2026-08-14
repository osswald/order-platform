## Purpose

Lets organisations brand the idle customer display with a synced image gallery that downloads once to the Pi and is cleared when gallery membership or the renting organisation changes.

## ADDED Requirements

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
