# pi-receipt-render-offload Specification

## Purpose

Speeds up Pi money-path responses by caching prepared receipt logos and building network print ESC/POS payloads in the print worker instead of on the submit request.

## Requirements

### Requirement: Receipt logo rasters are reused for identical inputs

When the Pi backend prepares an event receipt logo for a given source image and target printable width, it SHALL reuse a previously prepared raster for that same source content and width within the process lifetime (until the process restarts or the cache entry is invalidated after a bundle pull that changes the logo). Prepared logos MUST continue to satisfy the paper-width and non-profile-padding contracts of `escpos-receipt-logo`.

#### Scenario: Second slip reuses prepared logo

- **WHEN** two network print jobs for the same event are rendered with the same logo-enabled profile and the same target logo width
- **THEN** the second render MUST produce a logo raster byte-identical to the first for that width
- **AND** logo preparation for that width MUST not re-decode and re-threshold the source image from scratch

#### Scenario: Width change uses a distinct prepared logo

- **WHEN** a logo is prepared for `58mm` (384 dots) and later for `53mm` (360 dots)
- **THEN** each width has its own prepared raster matching that width’s printable-dot contract

#### Scenario: Bundle logo change invalidates cache

- **WHEN** a sync pull replaces the event’s `logo_base64` / `receipt_logo_base64` with different content
- **THEN** the next logo-enabled render MUST use a raster derived from the new content, not a stale cached raster

### Requirement: Network PrintJobs defer ESC/POS byte generation

Creating a queued network `PrintJob` for station, customer-pickup, voucher (network), or payment-receipt jobs MUST NOT require building the final ESC/POS payload on the HTTP request path. The system SHALL persist enough render context with the job for the print worker to build the payload later, then send it. Until render succeeds, the job MUST remain eligible for worker processing (not marked `sent`). Cash-drawer kicks MAY keep sync prebuilt payloads (no logo).

#### Scenario: Order create returns before station slip bytes exist

- **WHEN** a cash-register or waiter order creates one or more station (or customer-pickup) network print jobs
- **THEN** the create response completes without waiting for ESC/POS logo rasterization for those jobs
- **AND** each job is later rendered and sent by the print worker (or marked `error` with `last_error` if render/send fails)

#### Scenario: Render failure is retrievable as print-job error

- **WHEN** the print worker cannot build ESC/POS for a deferred job (corrupt context, missing order, invalid logo that fails closed after logging)
- **THEN** the job status becomes `error` with a non-empty `last_error`
- **AND** the HTTP request that enqueued the job is unaffected (already completed)

### Requirement: Client-returned ESC/POS payloads stay synchronous

Endpoints and create-order paths that return ESC/POS bytes to the client for Bluetooth or preview (including `voucher_escpos_payloads` and payload-returning payment/test APIs) SHALL continue to build those payloads before the response is returned. Those paths MUST use the same logo-preparation cache and visual contracts as deferred network renders.

#### Scenario: Bluetooth voucher slips still in create response

- **WHEN** a waiter order is created with `voucher_print_via_bluetooth` and voucher-sale lines
- **THEN** the create response includes base64 `voucher_escpos_payloads` as today
- **AND** those payloads are built before the response returns

#### Scenario: Payment receipt payload API remains sync

- **WHEN** a client requests a payment-receipt ESC/POS payload that is returned in the HTTP body
- **THEN** the payload is fully built in that request
- **AND** logo sizing still follows `escpos-receipt-logo` for the requested paper width
