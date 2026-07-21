# pi-event-safe-ota Specification

## Purpose
Keep production Pi appliances from applying GHCR container updates during live `prod` events, and apply updates outside those windows with minimize-outage pre-pull, required health checks, digest blacklist, free-space gating, and conservative image prune.

## Requirements

### Requirement: Prod event freezes container apply

The Pi host OTA mechanism MUST NOT pull or apply edge container image updates while any event in the currently synced config bundle has status `prod`, unless an explicit emergency override is set. Events in `test`, `config`, or `archive` alone MUST NOT freeze updates. The freeze signal MUST be derived from local synced bundle state and be readable by the host update process without requiring a successful HTTP call to the Pi backend.

#### Scenario: Freeze while a synced event is prod

- **WHEN** the synced config bundle contains at least one event whose status normalizes to `prod`
- **AND** the emergency override is not set
- **THEN** a scheduled or delayed-startup OTA run MUST exit without pulling images and without recreating containers

#### Scenario: Updates allowed when no prod event is synced

- **WHEN** the synced config bundle has no event with status `prod` (for example only `test`, or an empty/unpaired device)
- **THEN** a scheduled OTA run MAY pull and apply newer images according to the minimize-outage flow

#### Scenario: Emergency override bypasses freeze

- **WHEN** the emergency override is set on the appliance
- **AND** a synced event is `prod`
- **THEN** the OTA run MAY proceed past the freeze gate (operators accept event-time risk), subject to free-space and health rules

### Requirement: Free-space gate before pull

Before pulling images, the OTA process MUST check free disk space on the filesystem used for Docker images against `OTA_MIN_FREE_BYTES` (default **2 GiB**, configurable via appliance environment). If free space is below the minimum, the OTA process MUST attempt a conservative dangling image prune, re-check free space, and only then skip pull/apply if still below the minimum. A free-space skip MUST NOT blacklist any digest and MUST leave running containers unchanged.

#### Scenario: Skip pull when disk stays too full after prune

- **WHEN** apply is otherwise allowed (no prod freeze, or override set)
- **AND** free space is below the configured minimum
- **AND** after a dangling prune attempt free space is still below the minimum
- **THEN** the OTA process MUST NOT pull or recreate containers
- **AND** MUST NOT add digests to the blacklist

#### Scenario: Prune then proceed when space recovers

- **WHEN** free space is below the configured minimum
- **AND** a dangling prune brings free space to at or above the minimum
- **THEN** the OTA process MAY proceed with pre-pull and the rest of the minimize-outage flow

#### Scenario: Pull allowed when enough free space

- **WHEN** free space is at or above the configured minimum
- **AND** apply is otherwise allowed
- **THEN** the OTA process MAY proceed with pre-pull and the rest of the minimize-outage flow

### Requirement: Minimize-outage apply flow

When updates are allowed and free space is sufficient, the Pi host OTA mechanism MUST pre-pull new images while the currently running containers continue to serve traffic, MUST health-check the new image(s) before stopping the live stack, then perform a short stop/start (compose recreate) onto the new images. It MUST NOT use a boot-blocking `docker compose pull` as a prerequisite for starting the last-known-good stack.

#### Scenario: Pre-pull then short apply

- **WHEN** a newer image digest is available for `pi-backend` and/or `pi-frontend` and apply is allowed
- **AND** pre-apply health of the new image(s) succeeded
- **THEN** the OTA process MUST download the new image(s) before stopping the running containers
- **AND THEN** MUST recreate containers in a single short apply step onto those images

#### Scenario: No-op when digests unchanged

- **WHEN** a pull completes and the resolved digests match the images already running
- **THEN** the OTA process MUST NOT recreate containers
- **AND** MUST NOT require a pre-apply health probe of unchanged images

### Requirement: Required health verification and bad-digest blacklist

Before stopping the live stack to apply a new digest, the OTA process MUST health-check each new image that would be applied using a one-shot / side container (without disrupting the running stack or claiming the live SQLite volume). After applying new images, the OTA process MUST verify that the stack is healthy via the existing HTTP `/health` endpoint (through the published frontend port). If pre-apply health fails because the new image is unhealthy, the OTA process MUST leave the live stack on the old images and MUST blacklist the failing digest(s). If post-apply verification fails, the OTA process MUST roll back to the previously running image digests when possible and MUST blacklist the failed digest(s) so a later OTA run does not attempt to apply the same digest again until a different digest is published. Blacklisted digests MUST NOT expire by elapsed time; only a newer digest, manual clear, or emergency override lifts the block.

#### Scenario: Pre-apply health required before recreate

- **WHEN** a newer non-blacklisted digest would be applied
- **THEN** the OTA process MUST run a pre-apply health check of that new image in a side container before stopping or recreating the live containers
- **AND** MUST NOT skip that check

#### Scenario: Successful apply after health checks

- **WHEN** pre-apply health of the new image(s) succeeded
- **AND** new images are applied
- **AND** `/health` becomes successful within the configured timeout
- **THEN** the OTA process MUST leave the new images running
- **AND** MUST NOT blacklist those digests

#### Scenario: Failed apply rolls back and blacklists

- **WHEN** new images are applied
- **AND** `/health` does not succeed within the configured timeout
- **THEN** the OTA process MUST attempt to restore the previously running image digests
- **AND** MUST blacklist the failed digest(s)
- **AND** a subsequent OTA run MUST skip applying those blacklisted digests while still eligible to apply a newer non-blacklisted digest

#### Scenario: Pre-apply failure keeps serving old containers

- **WHEN** a pre-apply health check of the newly pulled image fails because the image is unhealthy
- **THEN** the OTA process MUST NOT stop or recreate the currently running containers
- **AND** MUST blacklist the failing digest

#### Scenario: Blacklist does not time-expire

- **WHEN** a digest has been blacklisted
- **AND** time has elapsed without a newer digest, manual clear, or emergency override
- **THEN** subsequent OTA runs MUST continue to skip applying that same digest

### Requirement: Prune unused images after successful apply or free-space pressure

The OTA process MUST attempt to reclaim disk by pruning dangling Docker images that are not required by the running stack in these cases: (1) after a successful apply (post-apply `/health` OK), and (2) when the free-space gate fails, before re-checking space. Prune MUST NOT run when apply was skipped for freeze, blacklist, or unchanged digests, when pre-apply health failed with the live stack unchanged, or when post-apply health failed and rollback ran. A prune command failure MUST be logged and MUST NOT reverse a successful apply.

#### Scenario: Prune after healthy apply

- **WHEN** new images have been applied and `/health` succeeded
- **THEN** the OTA process MUST attempt an image prune that does not remove images required by currently running containers
- **AND** the overall OTA run MUST still be considered successful if prune itself fails

#### Scenario: Prune when free-space gate fails

- **WHEN** free space is below the configured minimum before pull
- **THEN** the OTA process MUST attempt a dangling image prune before deciding the gate has finally failed

#### Scenario: No prune on freeze, blacklist skip, or health failure

- **WHEN** OTA skips because of prod freeze, blacklist, or unchanged digests
- **OR** apply fails health checks and rollback runs
- **OR** pre-apply health fails without recreating containers
- **THEN** the OTA process MUST NOT prune images as part of that run (except the free-space-pressure path above)

### Requirement: Delayed startup OTA uses the same gated flow

On device boot, the Pi MUST start the edge stack from images already present on the device without waiting on GHCR. After a **5 minute** delay (`OnBootSec=5min`), the same OTA mechanism used by the periodic timer MUST run (respecting prod freeze, free-space gate, blacklist, pre-pull, required health checks, rollback, and prune rules).

#### Scenario: Boot starts last-known-good without pull

- **WHEN** the Pi boots and starts the Vendiqo edge stack
- **THEN** startup MUST NOT block on `docker compose pull` from GHCR
- **AND** MUST bring up containers from images already available locally

#### Scenario: Delayed post-boot OTA after five minutes

- **WHEN** five minutes have elapsed since boot
- **AND** apply is allowed (no prod freeze, or override set)
- **AND** free space is sufficient (including after prune-on-pressure if needed)
- **THEN** the minimize-outage OTA flow MUST run
- **WHEN** a synced event is `prod` and override is unset
- **THEN** that delayed run MUST skip pull and apply
