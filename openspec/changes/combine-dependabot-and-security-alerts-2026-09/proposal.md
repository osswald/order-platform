## Why

GitHub currently shows eight grouped Dependabot PRs (#313, #315, #317–#322), eleven open Dependabot security alerts, and two open CodeQL findings on the cloud admin UI (XSS via `location.assign`, open redirect after login). Merging the bot PRs one-by-one wastes CI and still leaves High `js-yaml` / `nanoid` and Moderate `postcss` alerts unpatched because those transitive floors are not in the grouped version bumps. Per the living `dependency-maintenance` spec, this work should land as one CI-verified maintainer PR.

## What Changes

- Combine the eight open Dependabot directory groups onto one branch cut from latest `main` (npm, uv, and `actions/setup-java` v6).
- Remediate Dependabot alerts the grouped PRs miss: `js-yaml` ≥ 4.3.1, `nanoid` ≥ 3.3.18, `postcss` ≥ 8.5.23 (overrides + lockfiles); take pypdf 6.16.2 from #318 and raise the cloud-backend pyproject floor.
- Fix CodeQL #21 and #22 by accepting only same-origin internal paths for post-login `redirect` and organisation/tenant hard-reloads.
- Close #313, #315, #317–#322 with supersede comments once the combined PR exists.
- No `VERSION` bump (use `release:*` labels if a release is desired).

## Capabilities

### New Capabilities

None — this change extends existing security and dependency-maintenance contracts.

### Modified Capabilities

- `dependency-maintenance`: Combined weekly batches MUST also land patched versions for open Dependabot alerts that grouped version PRs did not include (transitive security floors / overrides).
- `cloud-security-baseline`: Cloud admin post-login navigation and organisation/tenant context hard-reloads MUST only assign same-origin relative paths (no protocol-relative or off-origin URLs).

## Impact

- **Lockfiles/manifests**: root, `cloud/frontend`, `pi/frontend`, `website` (`package.json` overrides + locks); `cloud/backend/pyproject.toml` + `uv.lock`; `pi/backend/uv.lock`; `cloud/hosted-pi-manager/uv.lock`
- **Workflows**: `.github/workflows/android-release.yml` (`actions/setup-java` v5 → v6)
- **Cloud frontend**: shared same-origin path helper used by `LoginPage.vue` and `useAuthSession.ts`
- **Tests**: new helper/login redirect tests; raise `package-audit` floors; full backend/frontend/lint matrix
- **PRs affected**: #313, #315, #317–#322 superseded by the combined PR
- **GitHub Security**: Dependabot alerts 63, 68–71, 73–74, 76–79 and Code scanning #21/#22 should clear after merge and graph refresh
- **Non-goals**: TypeScript 7; Pi login redirect hardening; dismissing CodeQL #2/#3 (existing won’t-fix); product features
