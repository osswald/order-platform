## Why

Seven Dependabot PRs (#214–#220, all created 2026-07-26) are open against `main`, one per grouped ecosystem directory. Merging them individually would waste CI and risk lockfile churn across npm and uv workspaces. Per the living `dependency-maintenance` spec and prior batches (#94, #134), they should land as one CI-verified combined PR, then the Dependabot PRs should be superseded with explicit comments.

## What Changes

Combine the seven open grouped updates onto one branch cut from latest `main`:

- **pi/frontend** (#214): `@types/node` 24.13.3 → 26.1.1
- **website** (#215): `markdown-it` 14.2.0 → 14.3.0; `vite` 8.0.16 → 8.1.5
- **cloud/hosted-pi-manager** (#216): `fastapi` 0.139.2 → 0.140.0
- **cloud/frontend** (#217): `vue-i18n` 11.4.7 → 11.4.8; `vuetify` 4.1.6; `@types/node` 24.13.3 → 26.1.1
- **root npm** (#218): **BREAKING** (tooling) `eslint` / `@eslint/js` 9 → 10; `eslint-plugin-vue` 10.9.2 → 10.10.0; `globals` 16.5.0 → 17.8.0; `typescript-eslint` 8.62.0 → 8.65.0
- **pi/backend** (#219): `fastapi` 0.139.2 → 0.140.0 (`uv.lock`)
- **cloud/backend** (#220): `fastapi` 0.139.2 → 0.140.0 (`uv.lock`)

No product features. No `VERSION` bump (use `release:*` labels if a release is desired). Close #214–#220 with supersede comments once the combined PR exists.

## Capabilities

### New Capabilities

None — dependency maintenance only.

### Modified Capabilities

- `dependency-maintenance`: Clarify that already-grouped Dependabot PRs (one per ecosystem directory) are still combined into a single maintainer PR when several directories update in the same weekly window; supersede comments remain required when closing #214–#220.

## Impact

- **Lockfiles/manifests**: root `package.json` + lockfile; `website/`; `cloud/frontend/`; `pi/frontend/`; `cloud/backend/uv.lock`; `pi/backend/uv.lock`; `cloud/hosted-pi-manager/pyproject.toml` + `uv.lock`
- **CI risk**: root ESLint 10 major may require flat-config / peer adjustments so `./scripts/lint.sh` stays green; FastAPI 0.140.0 needs both backend suites; `@types/node` 26 is types-only (runtime stays Node 24)
- **Runtime**: FastAPI minor across three Python apps; frontend/website bumps are patch/minor except `@types/node` major (devDependency)
- **PRs affected**: #214–#220 superseded by the combined PR
