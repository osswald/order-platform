## Why

Production Pi appliances auto-apply GHCR `:*-latest` images about every 15 minutes (and again on boot via `docker compose pull`). During a live `prod` event that has caused mid-service outages, crash loops from bad images, and forced power-cycles or SSH hotfixes. Venue POS must not restart or replace containers while a synced event is in production.

## What Changes

- Freeze container **apply** (and boot-time apply) while any synced config-bundle event has status `prod`.
- Replace blind `pull` + `up -d` with a **minimize-outage** OTA path:
  1. Refuse to pull when free disk space is below a configured minimum
  2. Pre-pull new images while old containers keep serving
  3. **Required** health-check of the new image(s) in a one-shot / side container before stopping the live stack
  4. Short stop → start onto the new image
  5. On health failure after apply (or failed pre-apply health check): abort, restore/keep the previous running image, and **blacklist that image digest** so the timer does not retry it until a newer digest appears
- Run the same OTA path on **device startup after a delay** (not an unbounded `ExecStartPre=pull` that can hang boot on flaky venue networks).
- **Prune** unused/dangling Docker images after a **successful** apply, and also when the free-space gate fails (then re-check space so a full SD of dangling layers can recover without waiting for a successful apply); never prune on health-failed apply/rollback or while frozen.
- Keep `test` / `config` / `archive`-only windows eligible for automatic updates so bad images can still be caught before `prod`.

## Capabilities

### New Capabilities

- `pi-event-safe-ota`: Rules for when the Pi host may pull and apply edge container updates, including free-space gating, required pre-apply and post-apply health checks, bad-digest blacklist, post-success image prune, and startup delayed OTA with a `prod` event freeze.

### Modified Capabilities

- (none)

## Impact

- **Pi host deploy units**: `vendiqo-pi-update.service` / `.timer`, `vendiqo-pi.service`, install/SD scripts under `pi/deploy/` and `sd-card-creator/` — update script becomes a gated OTA flow instead of raw compose pull/up.
- **Pi backend**: Sync / bundle handling writes or clears an on-disk freeze signal (and possibly exposes a small local status for operators); no cloud API schema change required for the freeze itself.
- **Pi images / GHCR**: No change to publish tags required for freeze; health-check and blacklist are local to the appliance.
- **Cloud admin / frontends**: None required for MVP (optional later: show “updates frozen” / blacklisted digest).
- **Ops**: Emergency override (`FORCE_UPDATE` or equivalent) must remain so a frozen or blacklisted Pi can still be recovered via SSH.
- **Out of scope for this change**: True zero-downtime / blue-green backend (SQLite single-writer), CI promote-to-`latest` soak pipeline.
