## Why

Hire-company operators managing server appliances in cloud can see each SD card’s pairing status and last-seen time, but not which Pi release is running. Confirming version today means physical access to Pi Admin. Piggybacking the existing edge sync path lets cloud show the Pi backend app version next to each SD card without a new connectivity model.

## What Changes

- Paired Pi backends include their running app version (`APP_VERSION`, optionally build time) on authenticated edge requests to cloud.
- Cloud persists the latest reported Pi backend version (and optional build time) on each `appliance_edge_credential`, updated alongside `last_seen_at`.
- Cloud appliance detail API exposes the reported version fields on edge credentials.
- Cloud Appliances UI SD-card table shows the reported Pi backend version (blank when never reported).
- Frontend PWA version is **out of scope** (backend/`APP_VERSION` only).

## Capabilities

### New Capabilities

- `cloud-sd-card-pi-version`: Pi reports backend app version to cloud on edge traffic; cloud stores and displays it on the server-appliance SD-card list.

### Modified Capabilities

- (none)

## Impact

- **Pi backend**: `cloud_client` request headers (or equivalent) carry version metadata already available via `version_info`.
- **Cloud backend**: `ApplianceEdgeCredential` schema/model, edge auth path that stamps `last_seen_at`, appliances read API / OpenAPI, Alembic migration.
- **Cloud frontend**: Appliances SD-card table column + i18n; regenerate OpenAPI types.
- **No** Pi frontend, Android, or OTA changes. No VERSION bump in the feature PR (use release label if desired).
