# Design: Combine open Dependabot dependency updates (July 2026)

## Context

Thirteen Dependabot PRs (#121–#133) are open against `main`. PR #120 (`chore/combine-dependabot-updates`) is already in flight and contains the Vuetify 4 / vue-router 5 migration plus ten earlier Dependabot bumps; it was just synced with `main` and its CI is green. Four of the new PRs overlap with #120:

| Dependabot PR | Target version | State in PR #120 |
|---------------|----------------|-------------------|
| #125 coverage-v8 4.1.10 (cloud) | 4.1.10 | already at 4.1.10 → obsolete |
| #129 vue-router 5.2.0 (cloud) | 5.2.0 | at 5.1.0 → small follow-up bump |
| #133 ts-eslint parser 8.64.0 (cloud) | 8.64.0 | at 8.63.0 → small follow-up bump |
| #127 ts-eslint parser 8.64.0 (pi) | 8.64.0 | at 8.63.0 → small follow-up bump |

The remaining nine PRs (#121, #122, #123, #124, #126, #128, #130, #131, #132) do not overlap with #120 at all.

## Goals / Non-Goals

**Goals:**
- Land all thirteen dependency updates on `main` with one CI-verified combined PR (plus the already-open #120)
- Avoid lockfile merge conflicts between Dependabot PRs and #120
- Close/auto-close all thirteen Dependabot PRs

**Non-Goals:**
- No `VERSION` bump (release labels handle that per `docs/RELEASE.md`)
- No feature or refactoring work; strictly dependency bumps
- No changes to Pi image tags or release process

## Decisions

1. **Merge #120 before combining the new updates** — #120 contains a framework migration (Vuetify 4) that four new PRs collide with. Rebasing #120 onto thirteen new bumps would be riskier than the reverse. Alternative considered: absorbing all thirteen into #120 — rejected because it re-triggers full review of an approved PR and grows an already large diff.

2. **Combine the remaining updates on one fresh branch (`chore/combine-dependabot-updates-2026-07`) instead of merging thirteen PRs individually** — matches repo precedent (#94, #120); one CI run, one review, no cascade of lockfile conflicts. Alternative: enable Dependabot grouped updates for the future (worth doing separately, out of scope here).

3. **Apply version bumps with the package managers, not by cherry-picking Dependabot commits** — `npm install <pkg>@<version>` in each frontend and editing the two `requirements-dev.txt` ranges reproduces the intent while producing a single consistent lockfile per workspace. Cherry-picks would conflict with each other in `package-lock.json`.

4. **Take the newest version where Dependabot targets an older base** — e.g. #129 was computed against vue-router 4.6.4 on `main`; after #120 merges, the branch simply bumps 5.1.0 → 5.2.0. Same for the two `@typescript-eslint/parser` bumps (8.63.0 → 8.64.0).

## Risks / Trade-offs

- [`actions/setup-node` v7 is a major bump] → CI-only change; verify the workflows' `node-version` inputs are still supported and CI passes before merge.
- [`vue` 3.5.40 / `vue-router` 5.2.0 could regress the fresh Vuetify 4 migration] → full frontend test suites + typecheck on the combined branch; the Vuetify 4 migration contract spec added on #120 guards the known slot-API regressions.
- [Dependabot PRs may not auto-close if resolved versions differ] → manually close leftovers with a comment pointing to the combined PR.
- [`httpx2` range widening (>=2.7.0) changes test-client behavior] → both backend test suites run in CI; run locally before pushing.

## Migration Plan

1. Merge PR #120 into `main`.
2. Branch `chore/combine-dependabot-updates-2026-07` from updated `main`; apply all bumps; run both backend suites, both frontend suites, typecheck, and lint.
3. Open the combined PR, referencing #121–#133; merge after CI.
4. Close any Dependabot PRs GitHub does not auto-close.

Rollback: revert the single combined merge commit.

## Open Questions

- Should Dependabot grouped updates be configured (`groups:` in `.github/dependabot.yml`) so future batches arrive pre-combined? (Recommended, separate change.)
