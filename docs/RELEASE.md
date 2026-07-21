# Releases and branch workflow

## Branch model

- **`main`** is the only long-lived branch. All changes land via pull request.
- Feature branches are short-lived (`feature/...`, `fix/...`, `chore/...`).
- Do **not** edit [`VERSION`](../VERSION) manually in PRs. The release automation updates it when you add a release label.

## Branch protection (GitHub settings)

Recommended settings on `main`:

| Setting | Value |
|---------|-------|
| Require pull request | Yes |
| Require approvals | 1 (your choice) |
| Dismiss stale approvals on new commits | Recommended |
| Block force pushes | Yes |
| Block deletions | Yes |
| Require status checks | **`PR gate / gate`** (after `.github/workflows/pr-gate.yml` is deployed) |
| Workflow permissions | **Settings → Actions → General → Read and write** |

On private repos without GitHub Team, classic branch protection rules apply. Rulesets may not enforce until you upgrade.

## Release labels

Add **exactly one** label to a PR when you want a semver release on merge:

| Label | When to use |
|-------|-------------|
| `release:patch` | Bugfixes (default) |
| `release:minor` | New features, backward compatible |
| `release:major` | Breaking changes |

PRs **without** a release label merge normally. Pi `*-latest` images still update on `main`, but there is no version bump, Git tag, or GitHub Release.

## What happens on merge

```text
1. You open a PR and add e.g. release:patch
2. release-prepare.yml bumps VERSION on the PR branch (may dismiss stale approval)
3. Reviewer re-approves; you merge
4. release.yml tags vX.Y.Z and creates a GitHub Release
5. pi-docker.yml builds and publishes Pi images on the `main` push
```

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [`pr-gate.yml`](../.github/workflows/pr-gate.yml) | Every PR | Always-on check for branch protection |
| [`release-prepare.yml`](../.github/workflows/release-prepare.yml) | PR labeled / updated | Bump `VERSION` on the PR branch |
| [`release.yml`](../.github/workflows/release.yml) | PR merged | Tag + GitHub Release |
| [`pi-docker.yml`](../.github/workflows/pi-docker.yml) | Push to `main` | Build and publish Pi Docker images |

## Pi Docker image tags

On every relevant push to `main`:

```text
ghcr.io/<owner>/<repo>:pi-backend-latest
ghcr.io/<owner>/<repo>:pi-frontend-latest
ghcr.io/<owner>/<repo>:pi-backend-amd64-latest
ghcr.io/<owner>/<repo>:pi-frontend-amd64-latest
ghcr.io/<owner>/<repo>:pi-backend-<sha>
ghcr.io/<owner>/<repo>:pi-frontend-<sha>
ghcr.io/<owner>/<repo>:pi-backend-<version>      # from VERSION on main
ghcr.io/<owner>/<repo>:pi-frontend-<version>
ghcr.io/<owner>/<repo>:pi-backend-amd64-<version>
ghcr.io/<owner>/<repo>:pi-frontend-amd64-<version>
```

Git tags (`v1.2.3`) are for GitHub Releases only — Docker images are not rebuilt on tag push.

### Pin a Pi to a release

Set in `pi/deploy/pi.prod.env` (or `/opt/vendiqo/pi/.env` on the device):

```bash
PI_BACKEND_IMAGE=ghcr.io/osswald/order-platform:pi-backend-1.2.3
PI_FRONTEND_IMAGE=ghcr.io/osswald/order-platform:pi-frontend-1.2.3
```

Then pull and restart:

```bash
sudo bash pi/deploy/apply-ghcr-images.sh
```

Leave defaults to follow `*-latest` (auto-update timer on production Pis). While any synced event is `prod`, the Pi OTA script freezes pull/apply (see `pi/README.md` — Event-safe OTA). Out of scope for OTA hardening: CI soak before promoting `:*-latest`.

## Local version bump script

For debugging only (CI uses this in workflows):

```bash
./scripts/bump-version.sh patch --print-only   # print next version
./scripts/bump-version.sh minor                  # write VERSION file
./scripts/test-bump-version.sh                   # run unit tests
```

## One-time repo setup

Run as repo admin (requires [`gh`](https://cli.github.com/)):

```bash
./scripts/configure-branch-protection.sh
```

Or manually:

1. Create labels `release:patch`, `release:minor`, `release:major`
2. Enable **Read and write** workflow permissions
3. Require **PR gate / gate** on `main` after the first merge with these workflows
