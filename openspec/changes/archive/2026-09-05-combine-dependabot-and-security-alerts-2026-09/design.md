## Context

Dependabot grouping is already enabled (`groups: patterns: ["*"]` per directory). The 2026-08-27 and 2026-09-03 weekly runs left eight open PRs, all CI-green:

| PR | Directory | Notable bumps |
|----|-----------|---------------|
| #313 | `/` (root npm) | OpenSpec 1.8.0 → 1.10.0; ESLint / globals / typescript-eslint |
| #315 | `/pi/backend` | SQLAlchemy 2.0.52; httpx2 2.12.0 |
| #317 | github-actions | `actions/setup-java` v5 → v6 in `android-release.yml` |
| #318 | `/cloud/backend` | gunicorn, SQLAlchemy, Alembic, fpdf2, **pypdf 6.14.2 → 6.16.2**, httpx2 |
| #319 | `/cloud/hosted-pi-manager` | pydantic 2.13.4 → 2.13.5 |
| #320 | `/website` | markdown-it 15.0.1 (ReDoS); Vite 8.2.2 |
| #321 | `/pi/frontend` | Vue / vue-router / Vite / tooling patches |
| #322 | `/cloud/frontend` | markdown-it 15.0.1; Vue / Vuetify / vue-i18n / tooling patches |

Open Dependabot alerts as of 2026-09-05:

| Severity | Package | Patch | Covered by grouped PRs? |
|----------|---------|-------|-------------------------|
| High | `js-yaml` `< 4.3.1` | 4.3.1 | No — locks still 4.3.0; overrides `^4.3.0` / `^4.2.0` |
| High | `nanoid` `< 3.3.18` | 3.3.18 | No — 3.3.17 (frontends), 3.3.16 (website) |
| Moderate | `postcss` `<= 8.5.22` | 8.5.23 | Partial — website already 8.5.23; cloud frontend 8.5.19 |
| Moderate | `pypdf` several GHSAs | 6.16.1+ | Yes — #318 → 6.16.2 |

Open CodeQL:

- #22 High `js/xss`: `window.location.assign(path)` in `useAuthSession.ts` where `path` is derived from `route.path`
- #21 Medium open redirect: `LoginPage.vue` accepts `route.query.redirect` if `startsWith('/')`, which still allows `//evil.com`

Prior combined batches (#94, #134, #222, #237) and `docs/dependency-updates.md` already define the combine/supersede playbook. No overlapping migration PR blocks these bumps.

## Goals / Non-Goals

**Goals:**

- Land all eight grouped updates plus the missed security floors in one combined, green PR
- Clear CodeQL #21 and #22 with a same-origin path check at both sinks
- Raise the cloud-backend `pypdf` pyproject floor so Dependabot cannot lag behind 6.16.1
- Supersede the eight bot PRs with comments naming the survivor
- Keep no `VERSION` bump in the feature PR

**Non-Goals:**

- TypeScript 7 (already ignored in `dependabot.yml`)
- Pi frontend `redirect` hardening (not in the current CodeQL set)
- Dismissing CodeQL #2/#3 (existing won’t-fix for edge credential files)
- Changing Dependabot schedule or grouping
- Regenerating Cursor OpenSpec skills solely because OpenSpec 1.10.0 lands
- Product features, OpenAPI schema changes, or Pi image tag updates

## Decisions

1. **One combined branch from latest `main`** — same playbook as #237 / #222. Apply bumps with package managers (`scripts/npm.sh`, `uv lock --upgrade-package`), not cherry-picks of Dependabot commits.

2. **Security floors ride in the same PR as the weekly bumps** — grouped PRs did not bump `js-yaml` / `nanoid` / cloud `postcss`. Leaving them for a follow-up would keep High alerts open after merge. Raise `overrides` in the affected `package.json` files and refresh locks. Prefer the shallowest override that lands the patched range.

3. **Same-origin helper, keep hard reload** — parse with `new URL(candidate, window.location.origin)` and accept only when `url.origin === window.location.origin`. Return `pathname + search + hash` (or a fallback). Keep `window.location.assign` / `href` so organisation/tenant switches still hard-reload; only constrain the URL. A `startsWith('/')` check is insufficient (protocol-relative URLs). Shared helper in `cloud/frontend/src/utils/safeInternalPath.ts` used by `LoginPage.vue` and `useAuthSession.ts`. Alternative rejected: replacing assign with `router.replace` — that would change the intended hard-reload behaviour.

4. **Include `actions/setup-java` v6** — major version, but the workflow only sets `distribution: temurin` and `java-version: "17"`. Upstream documents the ESM migration as not user-facing for this usage. Isolating it would leave a second PR open without reducing CI cost.

5. **Raise pypdf floor in pyproject, not lock-only** — #318 updates `uv.lock` to 6.16.2. Also set `pypdf>=6.16.1,<7` in `cloud/backend/pyproject.toml` so the next weekly run cannot resolve back below the advisory floor.

6. **Raise package-audit test floors** — `pi/frontend/tests/package-audit.test.ts` currently asserts js-yaml ≥ 4.2.0. Raise to 4.3.1 and add nanoid/postcss (and js-yaml) assertions for cloud frontend so the Highs cannot regress silently.

7. **Take OpenSpec 1.10.0 as a lockfile/manifest bump only** — do not regenerate `.cursor/skills` in this PR unless install scripts force it.

## Risks / Trade-offs

- [vue-router 5.2 → 5.3 or Vuetify 4.1.8 → 4.1.12 behavioural change] → Cloud + pi frontend tests and cloud typecheck are the gate; revert that workspace bump only if CI fails after the helper is already green.
- [npm overrides pin transitives] → Document each override with the GHSA; revisit when parents declare a patched range.
- [setup-java v6 breaks Android release workflow] → Isolated to `workflow_dispatch`; if apply-time docs show a breaking input rename, keep v5 and close #317 with an ignore comment instead of blocking the rest of the batch.
- [CodeQL still flags after origin check] → If GitHub’s sanitizer set does not recognise `URL` origin comparison, fall back to assigning `url.pathname + url.search` from a constructed same-origin `URL` object (taint-neutral sink pattern). Do not dismiss #21/#22 without a written rationale.
- [Dependabot PRs not auto-closing] → Manual close with `Superseded by #N — combining with …` per `docs/dependency-updates.md`.
- [Alerts stay open after merge until graph refresh] → Expected; re-check Security tab before dismissing.

## Migration Plan

1. Feature branch from updated `main` (no `VERSION` bump). Write helper tests first, then the helper, then dependency bumps and floors.
2. Run cloud + pi backend pytest, cloud frontend tests + typecheck, pi frontend tests, website tests if that lockfile changed, and `./scripts/lint.sh`.
3. Open one combined PR referencing #313, #315, #317–#322 plus the extra floors and CodeQL #21/#22.
4. Comment + close each Dependabot PR as superseded.
5. After merge, wait for dependency-graph refresh before dismissing leftover Dependabot alerts.

Rollback: revert the single combined merge commit.

## Open Questions

None blocking. Confirm at apply time that `js-yaml@4.3.1` and `nanoid@3.3.18` are published on npm before pinning overrides.
