## ADDED Requirements

### Requirement: FastAPI minor bumps stay aligned across uv apps
When a weekly Dependabot window bumps FastAPI in more than one of cloud backend, pi backend, and hosted-pi-manager, the combined maintainer PR MUST land the same FastAPI version in all three `uv.lock` files (and any corresponding lock refresh for hosted-pi-manager).

#### Scenario: Three uv apps share a FastAPI target
- **WHEN** open Dependabot PRs propose the same FastAPI minor/patch for `/cloud/backend`, `/pi/backend`, and `/cloud/hosted-pi-manager` in one weekly window
- **THEN** the combined PR upgrades all three locks to that FastAPI version together
- **AND** the combined PR is not split so that one uv app remains on the previous FastAPI version
