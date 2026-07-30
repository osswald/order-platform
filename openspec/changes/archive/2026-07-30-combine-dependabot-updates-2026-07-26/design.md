## Context

Dependabot grouping is already enabled (`groups: patterns: ["*"]` per directory in `.github/dependabot.yml`). The 2026-07-26 weekly run opened seven PRs — one per watched tree:

| PR | Directory | Notable bumps |
|----|-----------|---------------|
| #214 | `/pi/frontend` | `@types/node` 24 → 26 |
| #215 | `/website` | `markdown-it` 14.3.0, `vite` 8.1.5 |
| #216 | `/cloud/hosted-pi-manager` | `fastapi` 0.140.0 |
| #217 | `/cloud/frontend` | `vue-i18n` 11.4.8, `vuetify` 4.1.6, `@types/node` 24 → 26 |
| #218 | `/` (root lint) | **ESLint 9 → 10**, `globals` 17, `typescript-eslint` 8.65.0 |
| #219 | `/pi/backend` | `fastapi` 0.140.0 |
| #220 | `/cloud/backend` | `fastapi` 0.140.0 |

No overlapping in-flight migration PR blocks these updates. Living `dependency-maintenance` still requires combining across directories into one CI-verified maintainer PR.

## Goals / Non-Goals

**Goals:**
- Land all seven updates on `main` via one combined, green PR
- Supersede #214–#220 with comments naming the survivor PR
- Keep Node runtime at 24; keep no `VERSION` bump in the feature PR

**Non-Goals:**
- Changing Dependabot schedule/grouping config
- Jumping product runtime to Node 26 (only `@types/node` majors)
- Product features, OpenAPI schema changes, or Pi image tag updates

## Decisions

1. **One combined branch (`chore/combine-dependabot-updates-2026-07-26`) from latest `main`** — same playbook as #94 / #134. Merging seven PRs serially would re-run the full matrix seven times and still need supersede hygiene.

2. **Apply bumps with package managers, not cherry-picks** — `uv lock` / `uv add` for FastAPI workspaces; `scripts/npm.sh install <pkg>@<ver>` (or equivalent) for npm trees. Cherry-picking Dependabot commits into one branch fights lockfile merge noise.

3. **Take ESLint 10 from #218 in the same batch** — root lint is shared by `./scripts/lint.sh`. Isolating ESLint 10 would leave six other PRs open and still require a second CI cycle. Alternative considered: ignore ESLint major and land the rest first — rejected unless lint fails hard; prefer fix-forward (config peers) in the combined PR.

4. **Accept `@types/node` 26 while runtime stays Node 24** — matches prior combined batch (#128 / archive 2026-07-17). Types may expose newer APIs; typecheck + frontend tests are the gate. Do not bump Docker/`node-version` to 26.

5. **Align FastAPI 0.140.0 across cloud backend, pi backend, and hosted-pi-manager in one commit set** — keeps the three uv apps on the same FastAPI minor.

## Risks / Trade-offs

- [ESLint 10 breaking flat-config / peers] → Run `./scripts/lint.sh` early; adjust root `eslint.config.*` / package peers if needed before opening the combined PR.
- [FastAPI 0.140.0 subtle API/behavior change] → Full cloud + pi backend pytest suites; hosted-pi-manager has no heavy test suite — smoke-import / lint of that package.
- [`@types/node` 26 vs Node 24 runtime] → No runtime bump; if typecheck fails on Node-26-only typings, pin `@types/node` to latest 24.x instead and comment ignore on that package major.
- [Dependabot PRs not auto-closing] → Manual close with `Superseded by #N — combining with …` per `docs/dependency-updates.md`.

## Migration Plan

1. Branch from updated `main`; apply all seven directory bumps via uv/npm.
2. Run cloud + pi backend tests, cloud frontend tests + typecheck, pi frontend tests, website build/lint if applicable, and `./scripts/lint.sh`.
3. Open combined PR referencing #214–#220; no `VERSION` change.
4. After merge (or when opening, if closing early), comment + close each Dependabot PR as superseded.

Rollback: revert the single combined merge commit.

## Open Questions

- None blocking. If ESLint 10 proves too disruptive mid-apply, split it into a follow-up PR and ignore that major in `dependabot.yml` with a written peer/compat reason.
