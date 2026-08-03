## Purpose

Reduces Pi appliance and cloud load from routine sync by reusing HTTP connections, serving conditional bundle/snapshot responses, skipping no-op local writes, and debouncing restore checks while idle.

## ADDED Requirements

### Requirement: Sync cycle reuses one HTTP client for cloud calls

Within a single automatic or manual sync cycle that talks to the cloud, the Pi SHALL perform bundle pull, operational-snapshot fetch (when performed), and outbox chunk uploads using one shared HTTP client instance for that cycle, rather than opening a new client per request.

#### Scenario: Outbox push with multiple chunks

- **WHEN** a sync cycle pushes two or more pending outbox rows to cloud
- **THEN** those uploads MUST share the same HTTP client instance for that cycle
- **AND** the cycle MUST still mark each row `acked` or `error` independently as today

#### Scenario: Pull then push in one cycle

- **WHEN** a sync cycle both pulls the organisation bundle and pushes outbox rows
- **THEN** pull and push MUST share the same HTTP client instance for that cycle

### Requirement: Cloud serves conditional organisation bundle responses

`GET /edge/v1/bundle` SHALL include a stable validator (`ETag` or equivalent version token) for the assembled organisation bundle. When the client sends a matching `If-None-Match` (or equivalent), the cloud SHALL respond with **304 Not Modified** and MUST NOT include a full bundle body. When the bundle content that would be returned has changed, the cloud SHALL respond with **200** and a full body plus an updated validator.

#### Scenario: Unchanged bundle returns 304

- **WHEN** an edge appliance requests the organisation bundle with `If-None-Match` equal to the current bundle validator
- **THEN** the response status MUST be 304
- **AND** the response MUST NOT include the full organisation bundle payload

#### Scenario: Changed bundle returns 200 with new validator

- **WHEN** an edge appliance requests the organisation bundle after configuration or catalog content for that org has changed
- **THEN** the response status MUST be 200
- **AND** the body MUST be the current bundle
- **AND** the validator MUST differ from the previous value for that org

### Requirement: Cloud serves conditional operational snapshot responses

`GET /edge/v1/sync/operational/snapshot` SHALL include a stable validator for the snapshot payload (honouring the same event-filter query semantics as today). When the client sends a matching conditional request, the cloud SHALL respond with **304 Not Modified** without a full snapshot body.

#### Scenario: Unchanged snapshot returns 304

- **WHEN** an edge appliance requests an operational snapshot with a validator matching the current snapshot for that scope
- **THEN** the response status MUST be 304
- **AND** the response MUST NOT include the full snapshot payload

### Requirement: Pi uses conditional pull and skips local rewrite on 304

The Pi SHALL persist the last successful bundle validator from cloud and send it on subsequent bundle pulls. On **304**, the Pi MUST NOT rewrite `SyncedBundle`, MUST NOT invalidate the receipt-logo raster cache solely because of that pull, and MUST treat the local bundle as current. On **200**, the Pi MUST persist the new body and validator and MUST invalidate the logo cache when the body changed. If cloud omits validators, the Pi SHALL fall back to comparing the downloaded body to the stored `json_body` (skip rewrite + logo clear when identical).

#### Scenario: Bundle 304 leaves local storage and logo cache intact

- **WHEN** a sync pull receives 304 for the organisation bundle
- **THEN** `SyncedBundle.updated_at` MUST remain unchanged
- **AND** prepared receipt logos cached in-process MUST remain valid after that pull

#### Scenario: Bundle 200 with new body updates storage and clears logo cache

- **WHEN** a sync pull receives 200 with a bundle body that differs from the stored body
- **THEN** the Pi MUST persist the new body and validator
- **AND** MUST invalidate the receipt-logo raster cache

#### Scenario: Fallback without cloud validators

- **WHEN** cloud returns 200 without a validator
- **AND** the downloaded body is identical to the stored `json_body`
- **THEN** the Pi MUST NOT rewrite `SyncedBundle` and MUST NOT clear the logo cache

### Requirement: Pi treats snapshot 304 as unchanged cloud operational state

When a restore check runs and the operational snapshot request returns **304**, the Pi SHALL skip restore application and MUST NOT require local open-order fingerprint comparison for that check. When the snapshot returns **200**, existing `needs_operational_restore` / `pi-operational-restore` behavior applies.

#### Scenario: Snapshot 304 skips restore work

- **WHEN** restore is enabled and a restore check fetches the snapshot
- **AND** cloud responds 304
- **THEN** the Pi MUST NOT call `restore_operational_snapshot`
- **AND** MUST record that a restore check completed

### Requirement: Operational restore checks are debounced while idle

When operational restore is enabled, the Pi SHALL still perform restore checks, but MUST NOT fetch the operational snapshot on every sync cycle while idle. A restore check MUST run when any of the following is true: the process has not yet completed a restore check since startup; the bundle changed on this cycle (200 with new body, or local fallback detected change); there is at least one `pending` or `error` outbox row; a manual pull/sync was requested; or the time since the last restore check exceeds the configured maximum idle interval (default five minutes). When a restore check runs and cloud state may have changed (200 snapshot), restore behavior MUST continue to satisfy `pi-operational-restore`.

#### Scenario: Idle cycles skip snapshot HTTP

- **WHEN** restore is enabled
- **AND** the last restore check was recent (within the max idle interval)
- **AND** the bundle did not change
- **AND** there is no pending or error outbox
- **THEN** the sync cycle MUST NOT call the operational snapshot endpoint

#### Scenario: Bundle change forces restore check

- **WHEN** a sync cycle applies a changed organisation bundle
- **AND** restore is enabled
- **THEN** that cycle MUST perform a restore check (conditional snapshot fetch)

#### Scenario: Pending outbox forces restore check

- **WHEN** restore is enabled
- **AND** at least one outbox row is `pending` or `error`
- **THEN** the sync cycle MUST perform a restore check

#### Scenario: Max idle interval forces restore check

- **WHEN** restore is enabled
- **AND** the time since the last restore check exceeds the configured maximum idle interval
- **THEN** the next sync cycle MUST perform a restore check even if the bundle is unchanged and the outbox is empty
