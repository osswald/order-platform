# dependency-maintenance Specification

## Purpose
Define how dependency updates (Dependabot PRs) are batched, verified, and merged, and how they interact with releases.

## Requirements
### Requirement: Dependabot opens grouped updates per ecosystem directory
`.github/dependabot.yml` MUST configure a `groups:` entry with `patterns: ["*"]` for each package-ecosystem directory (npm frontends, uv backends / hosted-pi-manager, github-actions) so weekly runs open one PR per directory instead of one PR per package.

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
