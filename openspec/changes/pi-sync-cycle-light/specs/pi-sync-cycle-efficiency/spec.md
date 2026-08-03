## Purpose

Reduces Pi appliance load from routine cloud sync by reusing HTTP connections, skipping no-op bundle writes, and debouncing operational restore checks while idle.

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

### Requirement: Identical bundle pull does not rewrite local storage

When a sync pull downloads an organisation bundle whose serialized body is identical to the currently stored `SyncedBundle` body, the Pi SHALL NOT rewrite that row and SHALL NOT invalidate the receipt-logo raster cache solely because of that pull.

#### Scenario: Unchanged bundle on idle venue

- **WHEN** cloud returns the same bundle body already stored locally
- **THEN** `SyncedBundle.updated_at` MUST remain unchanged
- **AND** prepared receipt logos cached in-process MUST remain valid after that pull

#### Scenario: Changed bundle still updates and clears logo cache

- **WHEN** cloud returns a bundle body that differs from the stored body
- **THEN** the Pi MUST persist the new body
- **AND** MUST invalidate the receipt-logo raster cache as today

### Requirement: Operational restore checks are debounced while idle

When operational restore is enabled, the Pi SHALL still fetch the cloud operational snapshot and evaluate restore need, but MUST NOT perform that fetch on every sync cycle while idle. A restore check MUST run when any of the following is true: the process has not yet completed a restore check since startup; the bundle body changed on this cycle; there is at least one `pending` or `error` outbox row; or the time since the last restore check exceeds the configured maximum idle interval (default aligned with several sync intervals, e.g. five minutes). When a restore check runs and fingerprints diverge, restore behavior MUST continue to satisfy `pi-operational-restore`.

#### Scenario: Idle cycles skip snapshot HTTP

- **WHEN** restore is enabled
- **AND** the last restore check was recent (within the max idle interval)
- **AND** the bundle body did not change
- **AND** there is no pending or error outbox
- **THEN** the sync cycle MUST NOT call the operational snapshot endpoint

#### Scenario: Bundle change forces restore check

- **WHEN** a sync cycle persists a changed bundle body
- **AND** restore is enabled
- **THEN** that cycle MUST fetch the operational snapshot and evaluate restore need

#### Scenario: Pending outbox forces restore check

- **WHEN** restore is enabled
- **AND** at least one outbox row is `pending` or `error`
- **THEN** the sync cycle MUST fetch the operational snapshot and evaluate restore need (subject to existing restore logic)

#### Scenario: Max idle interval forces restore check

- **WHEN** restore is enabled
- **AND** the time since the last restore check exceeds the configured maximum idle interval
- **THEN** the next sync cycle MUST fetch the operational snapshot and evaluate restore need even if the bundle is unchanged and the outbox is empty
