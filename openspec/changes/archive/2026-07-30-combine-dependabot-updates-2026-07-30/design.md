## Context

Dependabot grouping is already enabled (`groups: patterns: ["*"]` per directory in `.github/dependabot.yml`). The 2026-07-30 weekly run opened six PRs — one per watched tree that had updates (no website PR this round):

| PR | Directory | Notable bumps |
|----|-----------|---------------|
| #231 | `/pi/frontend` | `@types/node` 26.1.1 → 26.1.2 |
| #232 | `/cloud/frontend` | `@types/node` 26.1.1 → 26.1.2 |
| #233 | `/` (root npm) | `@fission-ai/openspec` 1.6.0 → 1.7.0 |
| #234 | `/cloud/hosted-pi-manager` | `fastapi` 0.141.1, `uvicorn` 0.52.0 |
| #235 | `/pi/backend` | `fastapi` 0.140.0 → 0.141.1 |
| #236 | `/cloud/backend` | `fastapi` 0.141.1, `stripe` 15.3.1 → 15.4.0 |

Prior batch #214–#220 landed via combined PR #222 (2026-07-26). That OpenSpec change is archived at `openspec/changes/archive/2026-07-30-combine-dependabot-updates-2026-07-26/` with its delta synced into the living `dependency-maintenance` spec. No overlapping in-flight migration PR blocks these updates (`stripe-accounts-v2` OpenSpec change is complete; Stripe bump here is a minor SDK release only).

## Goals / Non-Goals

**Goals:**
- Land all six updates on `main` via one combined, green PR
- Keep FastAPI 0.141.1 aligned across cloud backend, pi backend, and hosted-pi-manager
- Supersede #231–#236 with comments naming the survivor PR
- Keep Node runtime at 24; keep no `VERSION` bump in the feature PR

**Non-Goals:**
- Changing Dependabot schedule/grouping config
- Jumping product runtime to Node 26
- Product features, OpenAPI schema changes, or Pi image tag updates
- Running `openspec update` to regenerate Cursor skills (optional follow-up after OpenSpec 1.7.0 lands)

## Decisions

1. **One combined branch from latest `main`** — same playbook as #222 / #202 / #134. Name follows cloud-agent convention (`cursor/combine-dependabot-updates-2026-07-30-2e77`).

2. **Apply bumps with package managers, not cherry-picks** — `uv lock --upgrade-package …` (or equivalent) for FastAPI / uvicorn / stripe; `scripts/npm.sh install <pkg>@<ver>` for npm trees. Avoid cherry-picking Dependabot commits into one branch.

3. **Keep hosted-pi-manager pyproject floors loose** — Dependabot #234 tightens `fastapi>=0.141.1` and `uvicorn[standard]>=0.52.0`. Prefer refreshing the lock to those versions while leaving floors at `>=0.115.0` / `>=0.51.0` (matches the 07-26 batch). Alternative considered: take Dependabot’s floor pins verbatim — rejected to avoid needlessly pinching lower bounds on every weekly bump.

4. **Include Stripe 15.4.0 in the same batch as FastAPI** — it rides in the cloud-backend group (#236). Isolating Stripe would leave a second PR open without reducing CI cost. Gate with cloud backend tests (including Stripe-related suites).

5. **Take OpenSpec 1.7.0 as a lockfile/manifest bump only** — do not regenerate `.cursor/skills` / commands in this PR unless install scripts force it; that can be a separate chore after merge.

6. **Accept `@types/node` 26.1.2 patch** — types-only; runtime stays Node 24. Cloud typecheck + both frontend test suites are the gate.

## Risks / Trade-offs

- [FastAPI 0.141.x behavior change] → Full cloud + pi backend pytest; hosted-pi-manager smoke-import / lint. New APIs (`app.frontend`) are unused in product code — low risk.
- [Stripe 15.4.0 subtle SDK change] → Cloud backend tests covering Connect / payment paths; skim release notes if tests fail.
- [uvicorn 0.52.0 on hosted-pi-manager only] → Acceptable for this batch (only #234 bumps it). Optionally align uvicorn in cloud/pi backend locks in the same PR if `uv lock --upgrade-package uvicorn` is cheap and CI stays green; not required.
- [OpenSpec 1.7.0 CLI behavior] → Root tooling only; `npx openspec list` / `validate` smoke after install if convenient.
- [Dependabot PRs not auto-closing] → Manual close with `Superseded by #N — combining with …` per `docs/dependency-updates.md`.

## Migration Plan

1. Branch from updated `main`; apply all six directory bumps via uv/npm.
2. Run cloud + pi backend tests, cloud frontend tests + typecheck, pi frontend tests, and `./scripts/lint.sh`.
3. Open combined PR referencing #231–#236; no `VERSION` change.
4. Comment + close each Dependabot PR as superseded.

Rollback: revert the single combined merge commit.

## Open Questions

- None blocking. Optional: whether to also bump `uvicorn` in cloud/pi backend locks to 0.52.0 for consistency — default is hosted-pi-manager only unless apply finds drift painful.
