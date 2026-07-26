## ADDED Requirements

### Requirement: Grouped directory Dependabot PRs still combine across workspaces
When Dependabot opens one grouped pull request per ecosystem directory in the same weekly window, maintainers MUST still combine those directory PRs into a single CI-verified maintainer branch cut from latest `main` (unless a documented ignore or sequencing constraint applies). Individual directory Dependabot PRs MUST receive an explicit supersede comment naming the survivor PR before or when they are closed without merge.

#### Scenario: Seven directory groups open in one week
- **WHEN** Dependabot has open grouped PRs for multiple watched directories (for example root npm, website, cloud/pi frontends, and uv backends) against `main`
- **THEN** maintainers apply the updates together on one combined branch using the package managers for each workspace
- **AND** the combined PR references the superseded Dependabot PR numbers
- **AND** each closed Dependabot PR receives a supersede comment before or at close

#### Scenario: Tooling major inside a directory group
- **WHEN** a grouped Dependabot PR includes a major bump limited to developer tooling (for example root ESLint 10)
- **THEN** the major is included in the same combined batch when `./scripts/lint.sh` (or equivalent) can be made green with config/peer fixes
- **AND** if the major cannot be landed, the PR is closed with an ignore instruction or `dependabot.yml` `ignore:` rule and a written peer/compat reason (not silently left open)
