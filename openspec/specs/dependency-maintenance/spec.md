# dependency-maintenance Specification

## Purpose
Define how dependency updates (Dependabot PRs) are batched, verified, and merged, and how they interact with releases.

## Requirements
### Requirement: Dependabot updates land as combined, CI-verified batches
When multiple Dependabot PRs are open, the maintainers SHALL combine them into a single branch cut from the latest `main`, and the combined branch MUST pass the full CI matrix (backend tests, frontend tests, typecheck, lint) before merge. Individual Dependabot PRs MUST be closed or auto-closed once the combined PR merges.

#### Scenario: Combining open Dependabot PRs
- **WHEN** more than one Dependabot PR is open against `main`
- **THEN** the updates are applied together on one combined branch using the package managers (npm / requirements ranges), producing one consistent lockfile per workspace
- **THEN** the combined PR references the superseded Dependabot PR numbers

#### Scenario: Overlap with an in-flight migration PR
- **WHEN** a Dependabot PR targets a dependency already changed by an open migration PR
- **THEN** the migration PR merges first and the combined branch bumps from the migrated version to the Dependabot target version

### Requirement: Combined update PRs do not bump VERSION
A combined dependency-update PR MUST NOT modify the `VERSION` file; releases are triggered via `release:patch|minor|major` labels per `docs/RELEASE.md`.

#### Scenario: Release labelling instead of VERSION edits
- **WHEN** a combined dependency-update PR is opened
- **THEN** the diff contains no `VERSION` change and a release label is applied if a release is desired
