# python-dependency-management Specification

## Purpose
Define how Python dependencies are declared, locked, installed, and updated across the monorepo: each Python project uses a PEP 621 `pyproject.toml` with a committed `uv.lock`, installs are frozen in Docker and CI, the shared package is consumed as an editable path source, and Dependabot keeps the lockfiles current.

## Requirements
### Requirement: Python projects declare dependencies in pyproject.toml with a committed lockfile
Each Python project in the monorepo (`cloud/backend`, `pi/backend`, `cloud/hosted-pi-manager`) SHALL declare its runtime dependencies in a PEP 621 `pyproject.toml` and its development dependencies in the `dev` dependency group, and SHALL commit a `uv.lock` lockfile that fully pins the resolved dependency tree. `requirements.txt` / `requirements-dev.txt` files MUST NOT be used.

#### Scenario: Lockfile is authoritative
- **WHEN** dependencies are installed for any Python project in CI or a Docker build
- **THEN** the install uses `uv sync --frozen` (or equivalent) so that the committed `uv.lock` fully determines the installed versions
- **AND** the build fails if `uv.lock` is out of sync with `pyproject.toml`

#### Scenario: Adding a dependency
- **WHEN** a developer adds or updates a dependency via `uv add` (or by editing `pyproject.toml` and running `uv lock`)
- **THEN** both `pyproject.toml` and the regenerated `uv.lock` are committed together

### Requirement: Projects lock independently
Each Python project SHALL have its own `pyproject.toml` and `uv.lock`; the repository MUST NOT define a root-level uv workspace that couples the projects' dependency resolution.

#### Scenario: Updating one project leaves the others untouched
- **WHEN** a dependency is updated in `pi/backend`
- **THEN** only files under `pi/backend/` change
- **AND** CI pipelines for `cloud/backend` and `cloud/hosted-pi-manager` are not triggered

### Requirement: Shared package consumed as an editable path source
`cloud/backend` and `pi/backend` SHALL depend on `vendiqo-shared` as an editable path dependency declared in `[tool.uv.sources]`, resolved from `packages/vendiqo_shared` within the repository.

#### Scenario: Shared package installed implicitly
- **WHEN** `uv sync` runs in `cloud/backend` or `pi/backend`
- **THEN** `vendiqo_shared` is installed in editable mode from the repository checkout without any separate install step

#### Scenario: Docker layout preserves the relative path
- **WHEN** a backend Docker image is built
- **THEN** the image build copies `packages/vendiqo_shared` and the project directory at paths matching their repo-relative layout so the lockfile's path source resolves

### Requirement: Production images exclude development dependencies
Backend Docker images SHALL install dependencies with a pinned uv binary using `uv sync --frozen --no-dev`, so that images contain only runtime dependencies and identical inputs produce identical dependency trees.

#### Scenario: Reproducible image build
- **WHEN** the same commit is built twice at different times
- **THEN** both images contain the same versions of every Python dependency

#### Scenario: Dev tooling excluded
- **WHEN** a production backend image is built
- **THEN** dev-group packages such as `pytest` and `pytest-cov` are not present in the image

### Requirement: uv version is pinned
Every place that installs or invokes uv (Dockerfiles, GitHub Actions workflows) SHALL pin an explicit uv version (0.11.29 at introduction) rather than tracking `latest`.

#### Scenario: Docker build uses the pinned binary
- **WHEN** a backend Docker image is built
- **THEN** the uv binary comes from a version-pinned source (e.g. `ghcr.io/astral-sh/uv:0.11.29`)

#### Scenario: CI uses the pinned version
- **WHEN** a workflow sets up uv via `astral-sh/setup-uv`
- **THEN** the step declares the pinned uv version explicitly

### Requirement: Ruff runs through uv
Python lint tooling SHALL be executed via `uvx ruff` in CI and in `scripts/lint.sh`, without a manual `pip install ruff` step. The local lint script MAY fall back to a preinstalled `ruff` binary or `python3 -m ruff` when uv is unavailable.

#### Scenario: CI lint job
- **WHEN** a ruff lint job runs in `.github/workflows/lint.yml`
- **THEN** ruff is invoked through uv with no pip install step

#### Scenario: Local lint without uv
- **WHEN** a developer without uv installed runs `./scripts/lint.sh` and a `ruff` binary is available
- **THEN** the script falls back to that binary and completes normally

### Requirement: Dependabot updates uv projects
Dependabot SHALL be configured with the `uv` package ecosystem for `cloud/backend`, `pi/backend`, and `cloud/hosted-pi-manager`, so that dependency update PRs modify `pyproject.toml` constraints and regenerate `uv.lock` together.

#### Scenario: Dependency update PR
- **WHEN** Dependabot opens an update PR for a Python project
- **THEN** the PR contains consistent changes to that project's `pyproject.toml` and/or `uv.lock` only
