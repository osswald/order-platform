## Context

See proposal.md — Why. Today `ApplianceEdgeCredential.last_seen_at` is updated inside cloud edge auth (`get_edge_appliance_context`) on every successful authenticated edge call. Pi `cloud_client._headers` only sends `X-Edge-Client-Id` / `X-Edge-Secret`. Pi already exposes `APP_VERSION` / `APP_BUILD_TIME` via `version_info` and `GET /health`. Cloud Appliances SD-card table shows label, client id, status, last seen.

## Goals / Non-Goals

**Goals:**

- Report Pi backend app version on existing edge traffic with minimal protocol change.
- Persist and expose the latest reported value per SD-card credential.
- Show it in the cloud SD-card table next to last seen.

**Non-Goals:**

- Reporting Pi frontend PWA or Android app versions.
- Fleet-wide “outdated devices” alerts or comparison to latest release.
- Cloud polling Pis or a dedicated heartbeat endpoint.
- Changing pairing, revoke, or OTA behavior.

## Decisions

### 1. Transport: optional request headers on all authenticated edge calls

**Decision:** Pi `cloud_client._headers` adds:

- `X-Edge-App-Version`: value from `get_app_version()` (required when reporting)
- `X-Edge-App-Build-Time`: value from `get_build_time()` when present

Cloud edge auth reads these headers when authenticating a credential and, if `X-Edge-App-Version` is non-empty, stores them on the credential while updating `last_seen_at`. Missing headers leave stored version fields unchanged (backward compatible with older Pis).

**Alternatives considered:**

- Dedicated `POST /edge/v1/status` — clearer but extra surface and another call cycle; rejected for v1.
- Body field on sync chunk/bundle — couples telemetry to sync payload schemas; rejected.

### 2. Storage: columns on `appliance_edge_credentials`

**Decision:** Add nullable columns:

- `reported_app_version` (string, e.g. 64)
- `reported_app_build_time` (string, nullable)

Updated only when a non-empty version header is present. No history table.

**Alternatives considered:**

- JSON `reported_runtime` blob — more flexible for future frontend version; deferred until needed.
- Appliance-level version — wrong grain; one server appliance can have multiple SD cards.

### 3. API / UI: single Version column

**Decision:** Extend `ApplianceEdgeCredentialRead` with `reported_app_version` and `reported_app_build_time`. Cloud SD-card table adds one “Version” column formatted like Pi Admin’s backend line (`v{version}` and optional ` ({build_time})` when build time is present and not `dev`). Empty/null → em dash or blank consistent with other empty cells.

**Alternatives considered:** Separate build-time column — clutter for little ops value.

### 4. Header size and validation

**Decision:** Accept only short printable strings (trim; max length aligned with DB columns). Ignore oversized or empty version headers without failing the request (auth and business logic must not break if a Pi sends garbage telemetry).

## Risks / Trade-offs

- [Older Pis never report] → Column stays empty until that image is upgraded once; document as expected.
- [Stale version after rollback without sync] → Same freshness as `last_seen_at`; show them together.
- [Header spoofing] → Same trust boundary as edge secret auth; only authenticated credentials can write their own row.
- [Extra DB writes on every edge call] → Already commit `last_seen_at` today; adding two string assigns is negligible. Optional micro-optimization later: skip write if values unchanged.

## Migration Plan

1. Ship cloud migration + API + UI (accepts headers; shows null until Pis report).
2. Ship Pi header reporting (can be same release or follow-up; safe either order).
3. Rollback: drop UI column and stop reading headers; columns can remain unused. Pi can stop sending headers without breaking cloud.

## Open Questions

None — frontend version and fleet alerts deferred by product choice.
