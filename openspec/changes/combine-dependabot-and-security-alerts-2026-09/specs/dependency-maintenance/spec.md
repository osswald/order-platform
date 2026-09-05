## ADDED Requirements

### Requirement: Combined batches include security floors grouped PRs missed
When a weekly Dependabot window leaves open security alerts whose patched versions are not present in the grouped version-update PRs (for example transitive packages only reachable via `overrides` or a parent bump), the combined maintainer PR MUST still land those patched versions in the corresponding lockfiles. Grouped version PRs MUST NOT be treated as complete remediations while those alerts remain open with a published patch.

#### Scenario: High transitive alert missing from grouped frontend PR
- **WHEN** a grouped Dependabot PR for `/cloud/frontend` or `/pi/frontend` does not bump an open High alert package that has a published `first_patched_version`
- **THEN** the combined maintainer PR updates that workspace lockfile (via parent bump or `overrides`) so the installed version is at or above the patched version
- **AND** the combined PR is not merged while that High alert’s package remains below the patched version on `main`

#### Scenario: Website or root lockfile still below a published patch
- **WHEN** an open Dependabot alert lists a patched version for a package in `/website` or the repository root lockfile
- **THEN** the combined maintainer PR lands that patched version even if the grouped PR for that directory only bumped unrelated packages
