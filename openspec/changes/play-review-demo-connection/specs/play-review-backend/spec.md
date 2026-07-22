## ADDED Requirements

### Requirement: Public health endpoint is backend JSON with CORS

The Play review host SHALL expose `GET https://play-review.demo.vendiqo.ch/health` as the Pi backend health API (JSON), not the SPA HTML shell, and SHALL include CORS headers that allow cross-origin reads from the Android WebView origin `https://appassets.androidplatform.net`.

#### Scenario: Health returns JSON

- **WHEN** a client requests `https://play-review.demo.vendiqo.ch/health`
- **THEN** the response SHALL be HTTP 2xx with `Content-Type` application/json (or equivalent JSON media type)
- **AND** the body SHALL include a healthy status indicator (e.g. `"status":"ok"`)

#### Scenario: Android WebView can read health cross-origin

- **WHEN** a browser or WebView with `Origin: https://appassets.androidplatform.net` requests `https://play-review.demo.vendiqo.ch/health`
- **THEN** the response SHALL include an `Access-Control-Allow-Origin` header that permits that origin (explicit reflection or `*`)

### Requirement: Deploy smoke check rejects SPA health

The play-review deploy verification SHALL treat a successful HTML document at `/health` as failure and SHALL only pass when public `/health` meets the JSON health requirement above.

#### Scenario: HTML health fails deploy

- **WHEN** deploy smoke checks `GET /health` and receives an HTML document (e.g. SPA `index.html`)
- **THEN** the deploy SHALL fail

#### Scenario: JSON health passes deploy

- **WHEN** deploy smoke checks `GET /health` and receives healthy JSON as specified
- **THEN** the deploy MAY proceed to sync and setup-status checks

### Requirement: Scheduled cleanup uses test→prod purge semantics

The Play review instance SHALL periodically clear demo operational data using the same purge behavior as an event **test → prod** transition (cloud `purge_event_operational_data` and Pi `purge_event_local_data` / equivalent), including emulated receipts on the Pi, without changing the demo event’s lasting status and without recreating the `pi-data` volume.

#### Scenario: Daily operational purge

- **WHEN** the scheduled Play review cleanup runs
- **THEN** orders and related operational rows for the Play Review Demo event SHALL be purged on cloud and Pi as in test→prod
- **AND** emulated receipts on the Play review Pi SHALL be removed
- **AND** edge pairing credentials and synced config bundle identity SHALL remain intact
- **AND** the demo event status SHALL remain unchanged (e.g. stay in `test` if that was configured)

#### Scenario: Cleanup does not require image deploy

- **WHEN** cleanup runs between Pi image publishes
- **THEN** the cleanup SHALL NOT require wiping the Docker `pi-data` volume

## MODIFIED Requirements

### Requirement: Persistent Play review host

The platform SHALL provide an always-on Pi backend reachable at `https://play-review.demo.vendiqo.ch` for Google Play review and smoke testing, independent of ephemeral per-event hosted Cloud-Pi sandboxes.

#### Scenario: Public HTTPS access

- **WHEN** a client on the public internet requests `https://play-review.demo.vendiqo.ch/health`
- **THEN** the request SHALL succeed with a healthy Pi backend JSON response

#### Scenario: Not subject to 24-hour hosted Pi TTL

- **WHEN** the Play review instance has been running for more than 24 hours
- **THEN** the instance SHALL remain available without automatic teardown
