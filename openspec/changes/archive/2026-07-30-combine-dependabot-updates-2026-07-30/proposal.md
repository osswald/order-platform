## Why

Six Dependabot PRs (#231–#236, all created 2026-07-30) are open against `main`, one per grouped ecosystem directory, after the previous batch landed in #222. Merging them individually wastes CI and risks lockfile churn. Per the living `dependency-maintenance` spec and prior combined batches (#94, #134, #222), they should land as one CI-verified maintainer PR, then the Dependabot PRs should be superseded with explicit comments.

## What Changes

Combine the six open grouped updates onto one branch cut from latest `main`:

- **pi/frontend** (#231): `@types/node` 26.1.1 → 26.1.2
- **cloud/frontend** (#232): `@types/node` 26.1.1 → 26.1.2
- **root npm** (#233): `@fission-ai/openspec` 1.6.0 → 1.7.0
- **cloud/hosted-pi-manager** (#234): `fastapi` 0.140.0 → 0.141.1; `uvicorn` 0.51.0 → 0.52.0
- **pi/backend** (#235): `fastapi` 0.140.0 → 0.141.1 (`uv.lock`)
- **cloud/backend** (#236): `fastapi` 0.140.0 → 0.141.1; `stripe` 15.3.1 → 15.4.0 (`uv.lock`)

No product features. No `VERSION` bump (use `release:*` labels if a release is desired). Close #231–#236 with supersede comments once the combined PR exists.

Also archives the completed `combine-dependabot-updates-2026-07-26` change (merged via #222) and syncs its delta requirement into the living `dependency-maintenance` spec.

## Capabilities

### New Capabilities

None — dependency maintenance only.

### Modified Capabilities

- `dependency-maintenance`: Add a requirement that when the same weekly window bumps FastAPI in more than one uv app (cloud backend, pi backend, hosted-pi-manager), the combined PR lands the same FastAPI version in all three locks.

## Impact

- **Lockfiles/manifests**: root `package.json` + lockfile; `cloud/frontend/`; `pi/frontend/`; `cloud/backend/uv.lock`; `pi/backend/uv.lock`; `cloud/hosted-pi-manager/` lock (and optionally floor pins — prefer lock-only refresh; see design)
- **CI risk**: FastAPI 0.141.1 needs cloud + pi backend suites; Stripe 15.4.0 needs cloud backend Stripe-related tests; `@types/node` patch is types-only; OpenSpec 1.7.0 is root tooling only
- **Runtime**: FastAPI minor across three Python apps; Stripe SDK minor on cloud only; frontend bumps are patch `@types/node`
- **PRs affected**: #231–#236 superseded by the combined PR
- **OpenSpec**: archive path `openspec/changes/archive/2026-07-30-combine-dependabot-updates-2026-07-26/`; main spec updated
