# play-review-backend Specification

## Purpose
Define the always-on Play review Pi host used for Google Play review, including deploy automation and demo event reset on code updates.

## Requirements

### Requirement: Persistent Play review host

The platform SHALL provide an always-on Pi backend reachable at `https://play-review.demo.vendiqo.ch` for Google Play review and smoke testing, independent of ephemeral per-event hosted Cloud-Pi sandboxes.

#### Scenario: Public HTTPS access

- **WHEN** a client on the public internet requests `https://play-review.demo.vendiqo.ch/health`
- **THEN** the request SHALL succeed with a healthy Pi backend JSON response

#### Scenario: Not subject to 24-hour hosted Pi TTL

- **WHEN** the Play review instance has been running for more than 24 hours
- **THEN** the instance SHALL remain available without automatic teardown

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

### Requirement: Review Pi uses production Pi images

The Play review stack SHALL run the same GHCR Pi backend and frontend images published by `pi-docker.yml` (`pi-*-amd64-latest` or version-pinned tags).

#### Scenario: Image pull on deploy

- **WHEN** a deploy workflow runs after new Pi images are published
- **THEN** the review stack SHALL pull updated images before restarting containers

### Requirement: Review Pi is pre-paired and synced

The Play review Pi backend SHALL start with edge credentials pre-configured (`HOSTED_PI=1` bootstrap) and SHALL synchronize configuration from the production cloud API.

#### Scenario: Setup status shows configured

- **WHEN** the review Pi backend has started successfully
- **THEN** `GET /v1/setup/status` SHALL report `configured: true` without manual pairing on the device

#### Scenario: Emulated printers

- **WHEN** the review Pi runs
- **THEN** `PRINTER_MODE` SHALL be `emulated` so receipt flows work without physical printers

### Requirement: Automated deploy after Pi image publish

The repository SHALL provide a GitHub Actions workflow that deploys or refreshes the Play review stack after a successful `pi-docker.yml` run on `main`.

#### Scenario: Deploy on main image publish

- **WHEN** `pi-docker.yml` completes successfully on `main`
- **THEN** the play-review deploy workflow SHALL update the VPS stack and verify reachability of the review host

#### Scenario: Deploy failure surfaces clearly

- **WHEN** the review host health check fails after deploy
- **THEN** the deploy workflow SHALL fail so maintainers are notified

### Requirement: Demo cloud data for review

Operators SHALL maintain a dedicated cloud organisation/event with demo waiters and products used exclusively by the Play review Pi, documented in repository operator docs.

#### Scenario: Waiter login on review instance

- **WHEN** a user connects the app to `https://play-review.demo.vendiqo.ch` and a demo bundle has been synced
- **THEN** documented demo waiters SHALL be able to log in with their configured PINs

### Requirement: Demo event resets on code deploy

Whenever the play-review stack is deployed after a Pi code update (`pi-docker.yml` on `main`), the review instance SHALL reset to a clean demo state before accepting traffic.

#### Scenario: Operational data wiped on deploy

- **WHEN** the play-review deploy workflow runs after new Pi images are published
- **THEN** the deploy SHALL remove local Pi operational data (orders, shifts, open tables, outbox) by recreating the Pi data volume or equivalent reset
- **AND** edge pairing credentials SHALL remain configured without manual re-pairing

#### Scenario: Fresh bundle after reset

- **WHEN** the review Pi has restarted after a deploy reset
- **THEN** the deploy workflow SHALL trigger a configuration sync (`POST /v1/sync/pull` or equivalent) so the demo event reflects current cloud config on a clean database

#### Scenario: Clean demo for reviewers

- **WHEN** a reviewer connects after a code deploy has completed
- **THEN** the demo event SHALL have no pre-existing orders or open tables from before that deploy
