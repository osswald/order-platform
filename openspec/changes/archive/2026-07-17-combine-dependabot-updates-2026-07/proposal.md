# Proposal: Combine open Dependabot dependency updates (July 2026)

## Why

Thirteen Dependabot PRs (#121–#133, all created 2026-07-16) are open against `main`. Several of them touch the same lockfiles as the in-flight combined-updates PR #120 (`chore/combine-dependabot-updates`, Vuetify 4 / vue-router 5 migration) and would conflict with it or with each other if merged individually. Following repo precedent (#94, #120), the updates should be combined into a single verified branch to keep CI runs and conflict resolution manageable.

## What Changes

Sequenced in two phases because PR #120 supersedes or conflicts with part of the Dependabot set:

**Phase 1 — land PR #120 first (already conflict-free, CI green)**
- Merging #120 makes Dependabot PRs #125 (`@vitest/coverage-v8` 4.1.10) obsolete and re-bases the target versions for #129 and #133.

**Phase 2 — combine remaining updates on a fresh branch from `main`**
- GitHub Actions: `actions/setup-node` 6 → 7 (#121)
- cloud/backend: `httpx2` >=2.5.0 → >=2.7.0 (#123)
- pi/backend: `httpx2` >=2.5.0 → >=2.7.0 (#122)
- cloud/frontend: `vue` → 3.5.40 (#131), `vue-router` → 5.2.0 (#129, supersedes the 5.1.0 from #120), `@vitejs/plugin-vue` → 6.0.8 (#126), `@typescript-eslint/parser` → 8.64.0 (#133)
- pi/frontend: `vue` → 3.5.40 (#132), `vite` → 8.1.5 (#124), `@vitejs/plugin-vue` → 6.0.8 (#130), `@types/node` → 26.1.1 (#128), `@typescript-eslint/parser` → 8.64.0 (#127)
- Close the individual Dependabot PRs once the combined PR merges (Dependabot auto-closes those whose versions are satisfied on `main`).

No breaking changes expected: all bumps are patch/minor except `actions/setup-node` (major, CI-only) and `vue-router` 5.1.0 → 5.2.0 (minor, already on v5 after #120).

## Capabilities

### New Capabilities

None — dependency maintenance only.

### Modified Capabilities

None — no spec-level behavior changes. All updates are implementation-level dependency bumps.

## Impact

- **Lockfiles/manifests**: `cloud/frontend/package.json` + lockfile, `pi/frontend/package.json` + lockfile, `cloud/backend/requirements*.txt`, `pi/backend/requirements*.txt`, `.github/workflows/*` (setup-node)
- **CI**: backend-tests, frontend-tests, lint, openapi-sync workflows must pass on the combined branch; setup-node 7 requires checking the workflow Node version matrix still resolves
- **Runtime**: none expected; `httpx2` is a test/dev dependency, frontend bumps are patch/minor within already-migrated majors
- **PRs affected**: #120 (must merge first), #121–#133 (superseded/closed by the combined PR)
