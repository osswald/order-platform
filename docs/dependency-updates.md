# Dependency updates and security alerts

How we handle Dependabot version PRs and GitHub Security alerts in this monorepo.

## Dependabot coverage

`.github/dependabot.yml` watches every committed lockfile tree:

| Ecosystem | Directories |
|-----------|-------------|
| npm | `/`, `/website`, `/cloud/frontend`, `/pi/frontend` |
| uv | `/cloud/backend`, `/pi/backend`, `/cloud/hosted-pi-manager` |
| github-actions | `/` |

Updates are **grouped** per directory (`patterns: ["*"]`) so weekly runs open one PR per workspace instead of one per package. Combined landing still follows the `dependency-maintenance` OpenSpec: one CI-verified PR, no `VERSION` bump (use `release:*` labels).

Cloud and Pi frontend entries **ignore TypeScript major** updates until `typescript-eslint` peers allow TypeScript 7 (`typescript@>=4.8.4 <6.1.0` today).

## Security-alert triage

When Dependabot or Code scanning reports an open alert:

1. **Prefer a fix** when a patched version exists — bump the parent, refresh the lockfile, or add a narrow `overrides` entry if the parent cannot reach the patched range. Land via a normal feature branch + CI.
2. **Dismiss only with a written rationale** when remediation is impossible or exploitability is clearly outside the product threat model (same bar as existing Code scanning won’t-fix notes for edge credential files on disk). Use a GitHub-supported dismissal reason and leave a human-readable comment on the alert.
3. Do **not** leave High alerts open solely because the directory was unwatched — extend Dependabot coverage instead.

## Dependabot PR lifecycle

When closing a Dependabot PR **without** merging it, leave a comment that states one of:

| Action | Comment pattern | When |
|--------|-----------------|------|
| **Supersede** | `Superseded by #N — combining with …` | Updates are landed in a combined maintainer PR |
| **Ignore** | `@dependabot ignore this major version` (and/or `ignore:` in `dependabot.yml`) plus the peer/compat reason | Known breaking majors (e.g. TypeScript 7) |
| **Already on main** | Note that `main` already satisfies the target version | Dependabot says “no longer updatable” — verify before treating as done |

Do not close Dependabot PRs silently. Grouped PRs may not honor one-off ignore comments; prefer `ignore:` in `dependabot.yml` for persistent peer conflicts.

## After merge

Security alerts often clear only after GitHub refreshes the dependency graph on the default branch. If an alert stays open after a fix has merged, wait for that refresh or re-check the Security tab before dismissing.
