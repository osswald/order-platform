# dependency-maintenance Specification

## Purpose
Define how dependency updates (Dependabot PRs) are batched, verified, and merged, how they interact with releases, and how Dependabot security alerts are remediated or dismissed.

## Requirements
### Requirement: Dependabot opens grouped updates per ecosystem directory
`.github/dependabot.yml` MUST configure a `groups:` entry with `patterns: ["*"]` for each package-ecosystem directory (npm lockfile roots including `/`, `/website`, and the frontends; uv backends / hosted-pi-manager; github-actions) so weekly runs open one PR per directory instead of one PR per package.

#### Scenario: Weekly Dependabot run with groups enabled
- **WHEN** Dependabot finds multiple dependency updates in `/cloud/frontend` (or another configured directory)
- **THEN** those updates are opened as a single grouped pull request for that directory

### Requirement: Dependabot updates land as combined, CI-verified batches
When multiple Dependabot PRs are open (for example before grouping, or across directories), the maintainers SHALL combine them into a single branch cut from the latest `main`, and the combined branch MUST pass the full CI matrix (backend tests, frontend tests, typecheck, lint) before merge. Individual Dependabot PRs MUST be closed or auto-closed once the combined PR merges.

#### Scenario: Combining open Dependabot PRs
- **WHEN** more than one Dependabot PR is open against `main`
- **THEN** the updates are applied together on one combined branch using the package managers (npm / uv), producing one consistent lockfile per workspace
- **THEN** the combined PR references the superseded Dependabot PR numbers

#### Scenario: Overlap with an in-flight migration PR
- **WHEN** a Dependabot PR targets a dependency already changed by an open migration PR
- **THEN** the migration PR merges first and the combined branch bumps from the migrated version to the Dependabot target version

### Requirement: Combined update PRs do not bump VERSION
A combined dependency-update PR MUST NOT modify the `VERSION` file; releases are triggered via `release:patch|minor|major` labels per `docs/RELEASE.md`.

#### Scenario: Release labelling instead of VERSION edits
- **WHEN** a combined dependency-update PR is opened
- **THEN** the diff contains no `VERSION` change and a release label is applied if a release is desired

### Requirement: Dependabot covers every npm lockfile directory
`.github/dependabot.yml` MUST include a `package-ecosystem: npm` entry for each directory in the repository that contains a committed `package-lock.json`, including the repository root (`/`) and `/website`, in addition to the existing frontend directories. Each such entry MUST use a `groups:` block with `patterns: ["*"]` consistent with other ecosystem directories.

#### Scenario: Root and website are watched
- **WHEN** Dependabot runs its weekly npm update check
- **THEN** it evaluates dependency updates for `/` and `/website` as well as `/cloud/frontend` and `/pi/frontend`
- **AND** updates within each directory are opened as one grouped pull request for that directory

### Requirement: Open Dependabot security alerts are remediable
When GitHub reports an open Dependabot security alert for a package in a watched manifest, maintainers MUST remediate by landing a patched version in the corresponding lockfile (via parent bump, `npm update`, or `overrides` when the parent cannot reach a patched range) in a CI-verified PR, unless a documented dismiss rationale applies under the triage requirement below.

#### Scenario: High alert with available patch is fixed in lockfile
- **WHEN** an open High Dependabot alert lists a `first_patched_version` for a package present in a committed lockfile
- **THEN** a pull request updates that lockfile so the installed version is at or above the patched version
- **AND** the repository’s applicable lint/test checks for the touched workspace pass

### Requirement: Security-alert triage prefers fix over dismiss
Maintainers MUST attempt a lockfile or dependency remediation for Dependabot security alerts that have a published patched version before dismissing. Dismissal (or “won’t fix”) is allowed ONLY when remediation is impossible or exploitability is clearly outside the product threat model, and MUST include a written rationale on the alert (same bar as existing Code scanning won’t-fix dismissals for edge credential storage).

#### Scenario: Dismiss only with written rationale
- **WHEN** a Dependabot or Code scanning alert is dismissed without a dependency/workflow change
- **THEN** the dismissal includes a human-readable comment explaining why the finding is not remediable or not applicable
- **AND** the reason is one of GitHub’s supported dismissal reasons

### Requirement: Dependabot PR close lifecycle is explicit
When closing a Dependabot pull request without merging it, maintainers MUST leave a comment that states one of: (a) superseded by a named combined PR number, (b) ignored via `@dependabot ignore …` (or an equivalent `ignore:` rule in `dependabot.yml`) with the peer/compat reason, or (c) no longer needed because `main` already satisfies the target version. Closing without such a comment is not allowed for Dependabot-authored PRs.

#### Scenario: Supersede into a combined PR
- **WHEN** maintainers combine several Dependabot updates into one PR
- **THEN** each superseded Dependabot PR receives a comment naming the survivor PR before it is closed

#### Scenario: Ignore an incompatible major
- **WHEN** a Dependabot PR proposes a major that breaks peer ranges (for example TypeScript 7 vs current typescript-eslint)
- **THEN** the PR is closed with an ignore instruction or config `ignore:` rule and a short comment naming the peer conflict
- **AND** the ignore does not silently strand security alerts on unwatched directories

### Requirement: Grouped directory Dependabot PRs still combine across workspaces
When Dependabot opens one grouped pull request per ecosystem directory in the same weekly window, maintainers MUST still combine those directory PRs into a single CI-verified maintainer branch cut from latest `main` (unless a documented ignore or sequencing constraint applies). Individual directory Dependabot PRs MUST receive an explicit supersede comment naming the survivor PR before or when they are closed without merge.

#### Scenario: Multiple directory groups open in one week
- **WHEN** Dependabot has open grouped PRs for multiple watched directories (for example root npm, website, cloud/pi frontends, and uv backends) against `main`
- **THEN** maintainers apply the updates together on one combined branch using the package managers for each workspace
- **AND** the combined PR references the superseded Dependabot PR numbers
- **AND** each closed Dependabot PR receives a supersede comment before or at close

#### Scenario: Tooling major inside a directory group
- **WHEN** a grouped Dependabot PR includes a major bump limited to developer tooling (for example root ESLint 10)
- **THEN** the major is included in the same combined batch when `./scripts/lint.sh` (or equivalent) can be made green with config/peer fixes
- **AND** if the major cannot be landed, the PR is closed with an ignore instruction or `dependabot.yml` `ignore:` rule and a written peer/compat reason (not silently left open)

### Requirement: FastAPI minor bumps stay aligned across uv apps
When a weekly Dependabot window bumps FastAPI in more than one of cloud backend, pi backend, and hosted-pi-manager, the combined maintainer PR MUST land the same FastAPI version in all three `uv.lock` files (and any corresponding lock refresh for hosted-pi-manager).

#### Scenario: Three uv apps share a FastAPI target
- **WHEN** open Dependabot PRs propose the same FastAPI minor/patch for `/cloud/backend`, `/pi/backend`, and `/cloud/hosted-pi-manager` in one weekly window
- **THEN** the combined PR upgrades all three locks to that FastAPI version together
- **AND** the combined PR is not split so that one uv app remains on the previous FastAPI version
