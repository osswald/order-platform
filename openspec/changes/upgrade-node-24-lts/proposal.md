## Why

The repository still targets Node 20 for CI, frontend Docker images, and TypeScript declarations, but Node 20 reached end-of-life in March 2026 and no longer receives security fixes. Moving to the current Active LTS (Node 24) restores a supported runtime while avoiding the shorter-lived Current line (Node 26).

## What Changes

- Bump the project Node runtime from **20** to **24 (Active LTS)** everywhere frontends are built or tested: GitHub Actions, cloud/pi frontend Docker images, website production image, and developer guidance (`AGENTS.md`).
- Align `@types/node` on cloud and pi frontends with Node 24 so compile-time APIs match the runtime.
- Make Pi Swiss money-format tests resilient to ICU group-separator differences across Node majors (known failure mode when moving off Node 20).
- **Out of scope:** jumping to Node 26 Current; Python/backend runtime changes; Dependabot batching policy.

## Capabilities

### New Capabilities
- `node-toolchain`: Defines the supported Node major version for frontend CI, Docker builds, TypeScript declarations, and locale-sensitive test expectations.

### Modified Capabilities
- *(none)* — `dependency-maintenance` covers Dependabot batching, not the project's chosen Node major.

## Impact

- **CI:** `.github/workflows/frontend-tests.yml`, `lint.yml`, `openapi-sync.yml` (`node-version: "20"` → `"24"`).
- **Docker:** `cloud/frontend/Dockerfile`, `cloud/frontend/Dockerfile.prod`, `pi/frontend/Dockerfile`, `pi/frontend/Dockerfile.prod`, `website/Dockerfile.prod` (`node:20-alpine` → `node:24-alpine`).
- **Packages:** `cloud/frontend` and `pi/frontend` `@types/node` → Node 24 line; lockfiles updated.
- **Docs:** `AGENTS.md` Node version guidance and Cloud VM nvm notes.
- **Tests:** `pi/frontend/src/utils/money.test.ts` (and any similar hard-coded ICU assertions) must pass on Node 24.
- **Release:** Prefer a single PR with `release:patch` (toolchain bump, no product feature).
