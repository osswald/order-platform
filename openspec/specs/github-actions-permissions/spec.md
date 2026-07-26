# github-actions-permissions Specification

## Purpose
Require least-privilege, explicit `GITHUB_TOKEN` permissions on every GitHub Actions workflow job so CodeQL Actions hygiene stays clear.

## Requirements
### Requirement: Every workflow job declares explicit token permissions
Every job in `.github/workflows/*.yml` MUST declare an explicit `permissions:` block (at workflow top level and/or on the job) so the job does not inherit ambient repository token defaults. Permissions MUST follow least privilege for that job’s steps (for example `contents: read` for checkout-only jobs; additional write scopes only where the job pushes packages, creates releases, or otherwise requires write access).

#### Scenario: Pi Docker guards job is scoped
- **WHEN** the `guards` job in `.github/workflows/pi-docker.yml` runs
- **THEN** that job has an explicit `permissions` block
- **AND** the permissions do not grant write scopes unnecessary for running the build-guard script

#### Scenario: No workflow job omits permissions
- **WHEN** a maintainer audits `.github/workflows/*.yml`
- **THEN** every job either inherits a workflow-level `permissions` block or defines its own
- **AND** CodeQL rule `actions/missing-workflow-permissions` does not report an open finding for those workflows after the audit lands on the default branch
