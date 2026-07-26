## Why

Dependabot and Code scanning currently show open High/medium findings (transitive npm CVEs plus one Actions permissions warning), but several affected lockfile trees are outside Dependabot’s configured directories, so alerts appear without fix PRs. Recent Dependabot PRs were closed for valid reasons (supersede / peer-conflict ignore), yet there is no written playbook for that lifecycle or for when to fix vs dismiss a security alert. Clearing the dashboard and preventing silent gaps needs a small, deliberate hygiene change now.

## What Changes

- Extend `.github/dependabot.yml` so every npm lockfile root is watched: add `/` (root lint tooling) and `/website`, with the same grouped-update pattern as the other directories.
- Remediate the six open Dependabot High alerts by bumping/resolving patched transitive versions in `package-lock.json`, `cloud/frontend/package-lock.json`, and `website/package-lock.json` (npm overrides only if a parent cannot reach a patched range).
- Fix CodeQL alert #19 by giving every job in `.github/workflows/pi-docker.yml` an explicit least-privilege `permissions` block (today only `build` / `merge` declare one).
- Document a security-alert triage policy: prefer lockfile/parent bumps for reachable Highs; dismiss only with a written rationale when exploitability is clearly outside our threat model (same bar as the existing edge-credential won’t-fix dismissals).
- Document the Dependabot PR lifecycle already practiced: combine/supersede with a comment referencing the survivor PR; use `@dependabot ignore …` (or `ignore:` in config) for known peer-incompatible majors (e.g. TypeScript 7 until eslint peers catch up); do not leave security alerts stranded on unwatched directories.

## Capabilities

### New Capabilities
- `github-actions-permissions`: Require every GitHub Actions workflow/job to declare explicit `permissions` so CodeQL `actions/missing-workflow-permissions` stays clear and GITHUB_TOKEN follows least privilege.

### Modified Capabilities
- `dependency-maintenance`: Dependabot MUST cover all npm lockfile directories in the monorepo (including root and website); security vulnerability alerts MUST have an automated update path or an explicit documented ignore/dismiss; maintainers MUST follow a defined close/combine/ignore playbook for Dependabot PRs.

## Impact

- **Config**: `.github/dependabot.yml`, `.github/workflows/pi-docker.yml` (and any other workflow found without `permissions` during audit)
- **Lockfiles**: root `package-lock.json`, `cloud/frontend/package-lock.json`, `website/package-lock.json` (and `package.json` `overrides` only if needed)
- **Docs**: short addition under `docs/` or AGENTS.md for Dependabot + security-alert hygiene (triage + PR lifecycle)
- **GitHub Security**: close or auto-resolve Dependabot alerts #52–#57 and Code scanning alert #19 after merge
- **Non-goals**: bumping TypeScript to 7; re-opening superseded httpx2/actions PRs already reflected on `main`; changing CodeQL default-setup languages/query suite; production app code changes unrelated to deps/workflows
