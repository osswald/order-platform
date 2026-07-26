## Context

GitHub Security currently shows:

| Source | Open | Nature |
|--------|------|--------|
| Dependabot | 6 High | Transitive npm: `brace-expansion`, `js-yaml` (root + cloud frontend), `linkify-it` + `postcss` (website) |
| Code scanning | 1 medium | `actions/missing-workflow-permissions` on `pi-docker.yml` `guards` job |

`.github/dependabot.yml` already groups updates for cloud/pi frontends, uv backends, hosted-pi-manager, and github-actions — but **not** root npm (`vendiqo-frontend-lint`) or `/website`. Alerts still appear from the dependency graph; Dependabot simply never opens fix PRs for those trees.

Recent Dependabot PR closures (#198–#201) were intentional, not bitrot:

- Superseded into a combined PR (#202) with a comment naming the survivor
- `@dependabot ignore this major version` for TypeScript 7 peer conflict with typescript-eslint
- httpx2 already at `>=2.9.1` on `main`, so Dependabot closed “no longer updatable”

`cloud/frontend` and `pi/frontend` already use `package.json` `overrides` for some packages. Root and website do not yet.

## Goals / Non-Goals

**Goals:**

- Close the six Dependabot Highs and the one CodeQL Actions alert via lockfile/workflow changes.
- Make Dependabot cover every npm lockfile directory in the repo.
- Codify triage (fix vs dismiss) and Dependabot PR lifecycle (combine / ignore / supersede) so future alerts do not stall silently.
- Keep every Actions job on explicit least-privilege `permissions`.

**Non-Goals:**

- Adopting TypeScript 7 (blocked by typescript-eslint peers; keep the ignore).
- Changing CodeQL default-setup languages or query suite.
- Application feature work, Stripe, or auth changes.
- Dismissing the six open Highs without attempting a patched lockfile first.
- Bumping `VERSION` (use release labels if a release is desired).

## Decisions

### 1. Prefer lockfile bumps; use `overrides` only when the parent cannot reach a patched range

- **Choice**: For each alert, run `npm update <pkg>` / bump parent / or `overrides` in that workspace’s `package.json`, then `npm install` to refresh the lockfile. Prefer the shallowest fix that lands a patched version.
- **Why**: Matches existing frontend override patterns; avoids forever-pinning transitive trees when a simple update works.
- **Alternative rejected**: Dismiss all tooling CVEs as “dev-only” without bumping — GitHub still counts them open; several (website `markdown-it` / Vite) sit on a public build path.

Current targets (as of exploration):

| Alert | Manifest | Fix direction |
|-------|----------|---------------|
| brace-expansion `<1.1.16` / `<5.0.7` | root | land `1.1.16` and `5.0.7` (eslint/minimatch chain) |
| js-yaml `<4.3.0` | root, cloud/frontend | land `4.3.0` (eslint / Redocly) |
| linkify-it `<=5.0.1` | website | land `5.0.2` (via markdown-it or override) |
| postcss `<=8.5.17` | website | land `≥8.5.18` (Vite toolchain) |

### 2. Extend Dependabot npm coverage to `/` and `/website`

- **Choice**: Add two `package-ecosystem: npm` entries with `groups:` + `patterns: ["*"]`, same weekly cadence and `open-pull-requests-limit: 5` as siblings.
- **Why**: Closes the silent-alert gap; keeps the existing “one PR per directory” batching contract in `dependency-maintenance`.
- **Alternative rejected**: Relying only on Security alerts without version-update PRs — that is how we got stranded Highs on website/root.

### 3. Fix `pi-docker.yml` at job level; audit other workflows once

- **Choice**: Add `permissions: contents: read` (or the minimum needed) to the `guards` job. Re-scan `.github/workflows/` for any job lacking `permissions`; fix stragglers in the same PR. Prefer job-level blocks where jobs need different writes (e.g. `packages: write` on build/merge).
- **Why**: CodeQL flagged line 32 (`guards`); sibling jobs already declare permissions. Workflow-wide `permissions: contents: read` plus job overrides also works, but job-level matches the file’s current style.
- **Alternative rejected**: Dismissing the CodeQL alert — cheapest fix is adding the block.

### 4. Triage policy: fix first; dismiss only with written rationale

- **Choice**: For Dependabot security alerts: (1) bump if a patched version exists and CI passes; (2) if no patch or exploitability is clearly outside the product threat model, dismiss with the same style of comment used for edge credential clear-text storage; (3) never leave Highs open solely because the directory was unwatched.
- **Why**: Keeps the Security tab meaningful without false “we ignored everything” debt.
- **Alternative rejected**: Auto-dismiss all npm tooling DoS advisories — too blunt; website postcss/linkify-it deserve a real bump.

### 5. Document Dependabot PR lifecycle (process already practiced)

- **Choice**: Short doc section (AGENTS.md or `docs/dependency-updates.md`) covering:
  1. **Combine**: when multiple Dependabot PRs are open, land one combined PR; comment on each Dependabot PR `Superseded by #N` then close.
  2. **Ignore**: for known peer-incompatible majors, `@dependabot ignore this major version` **and** optionally add `ignore:` in `dependabot.yml` so group PRs do not keep proposing the same break.
  3. **Do not panic-close**: if Dependabot says “no longer updatable”, verify `main` already has the target version before treating it as done.
- **Why**: #198–#201 show the process works when commented; writing it down prevents “why were these closed?” thrash next time.

### 6. Optional `ignore` for TypeScript major in frontend groups

- **Choice**: If TS 7 keeps reappearing in grouped frontend PRs despite the ignore comment, add an explicit `ignore:` rule for `typescript` major updates under cloud/pi frontend Dependabot entries.
- **Why**: Grouped updates do not always honor one-off ignore comments the way single-package PRs do (Dependabot warned about this on #199).
- **Defer** if after coverage/fix work the next weekly run stays quiet.

## Risks / Trade-offs

- [npm overrides pin transitive versions] → Prefer parent bumps first; document any override with a one-line comment pointing at the GHSA; revisit when the parent releases a patched range.
- [Root eslint bump pulls unrelated majors] → Constrain updates to the vulnerable packages / patch-level where possible; run `./scripts/lint.sh` after.
- [Website lockfile refresh changes Vite patch] → Run `website` build (`npm ci && npm run build`) in verification; site is static marketing, low regression surface.
- [Dependabot noise from newly covered directories] → Grouped updates + existing combine playbook; same `open-pull-requests-limit`.
- [CodeQL re-fires on a different workflow later] → Spec requires all workflows/jobs to declare permissions; audit once in this change.

## Migration Plan

1. Feature branch from `main` (no `VERSION` bump).
2. Dependabot.yml coverage → lockfile remediations → `pi-docker` permissions → short docs.
3. Verify: lint, affected frontend/website builds, confirm GitHub Security alerts resolve after merge (may take a dependency-graph refresh).
4. Rollback: revert the PR; alerts reappear — acceptable for a hygiene change.

## Open Questions

- None blocking implementation. Confirm at apply time whether website `node_modules` are present locally (`npm ci` in `website/`) before updating that lockfile.
