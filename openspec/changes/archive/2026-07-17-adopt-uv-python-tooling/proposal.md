## Why

The three Python services (`cloud/backend`, `pi/backend`, `cloud/hosted-pi-manager`) declare dependencies in `requirements.txt` files that are largely unpinned (`fastapi`, `sqlalchemy`, `alembic` carry no version constraints at all). Docker and CI builds are therefore not reproducible: the same commit can produce different dependency trees over time, and an upstream minor release can break CI or production images with no change in git. Dependabot can only bump constraints that exist, so unpinned dependencies drift silently underneath it.

Adopting **uv** gives every Python project a `pyproject.toml` with explicit constraints plus a committed `uv.lock`, making builds reproducible while also simplifying the repeated `pip install -e packages/vendiqo_shared` boilerplate in Dockerfiles and CI, and speeding up installs (notably the QEMU-emulated ARM image builds for the Pi).

## What Changes

- Convert `cloud/backend`, `pi/backend`, and `cloud/hosted-pi-manager` from `requirements.txt` / `requirements-dev.txt` to `pyproject.toml` with a committed `uv.lock` each (dev dependencies via `[dependency-groups]`).
- Keep the three projects **independent** (no root uv workspace): each locks on its own, preserving the per-directory Dependabot setup and path-filtered CI. `packages/vendiqo_shared` becomes an editable path dependency (`[tool.uv.sources]`) of `cloud/backend` and `pi/backend`.
- Update the four backend Dockerfiles (`cloud/backend/Dockerfile[.prod]`, `pi/backend/Dockerfile`, `cloud/hosted-pi-manager/Dockerfile`) to install with a pinned uv binary and `uv sync --frozen --no-dev`.
- Update CI workflows (`backend-tests.yml`, `openapi-sync.yml`) to set up uv and run tests via `uv run`, replacing the manual pip install steps.
- Install ruff via uv as well: `lint.yml` and `scripts/lint.sh` run ruff through `uvx` instead of `python -m pip install ruff`.
- Pin uv at **0.11.29** (latest stable) in all Dockerfiles and workflows.
- Switch the two `pip` Dependabot ecosystems to `uv` and add one for `cloud/hosted-pi-manager`.
- Update developer documentation (`AGENTS.md`, `README.md`) with the uv-based commands.
- Remove the now-obsolete `requirements*.txt` files.
- While migrating, verify every declared dependency is real and needed (e.g. `httpx2` in both dev requirement files looks like a typo).

**BREAKING** (dev workflow only): contributors install dependencies with `uv sync` instead of `pip install -r requirements.txt`; runtime behavior of the services is unchanged.

## Capabilities

### New Capabilities

- `python-dependency-management`: How Python dependencies are declared, locked, installed, and updated across the monorepo (pyproject + uv.lock per project, frozen installs in Docker/CI, Dependabot integration).

### Modified Capabilities

<!-- none: no existing spec covers dependency management -->

## Impact

- **Code/config**: `cloud/backend`, `pi/backend`, `cloud/hosted-pi-manager` (new `pyproject.toml` + `uv.lock`, removed `requirements*.txt`); `packages/vendiqo_shared` unchanged apart from being referenced as a path source.
- **Docker**: 4 backend Dockerfiles; Pi ARM image build (`pi-docker.yml`) gets faster installs under QEMU.
- **CI**: `.github/workflows/backend-tests.yml`, `.github/workflows/openapi-sync.yml`, `.github/workflows/lint.yml`, `.github/dependabot.yml`, `.github/filters.yaml` (path filters must match the new files).
- **Lint**: `scripts/lint.sh` (ruff invocation via uv).
- **Docs**: `AGENTS.md`, `README.md`, `cloud/README.md` where install/test/lint commands are shown.
- **Not in scope**: frontends (npm), Pi device runtime behavior.
