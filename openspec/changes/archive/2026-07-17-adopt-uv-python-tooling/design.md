## Context

Three Python services are installed from `requirements.txt` / `requirements-dev.txt` with mostly unpinned constraints, plus a shared package `packages/vendiqo_shared` (standard `pyproject.toml`, setuptools backend) that is installed via a repeated `pip install -e packages/vendiqo_shared` step in three Dockerfiles and two CI workflows. There is no lockfile anywhere, so image and CI builds are not reproducible. Dependabot watches the two backend `pip` directories; CI is path-filtered per project (`.github/filters.yaml`); Pi images are built for `linux/arm64` under QEMU (`pi-docker.yml`).

## Goals / Non-Goals

**Goals:**

- Reproducible installs everywhere (dev, CI, Docker) via committed lockfiles.
- One declaration format (`pyproject.toml`) for all Python projects, including dev dependencies.
- Remove the copy-pasted editable install of `vendiqo_shared` from CI (it stays a one-line source declaration per project).
- Keep Dependabot coverage, and extend it to `cloud/hosted-pi-manager`.
- Faster installs, especially in QEMU-emulated ARM builds.

**Non-Goals:**

- No root-level uv workspace (see Decisions).
- No change to `vendiqo_shared`'s build backend or packaging.
- No change to frontend tooling or Pi runtime behavior.
- No dependency upgrades beyond what re-resolution requires; upgrades stay Dependabot's job.

## Decisions

### 1. uv, not Poetry or pip-tools

uv provides lockfiles with standard PEP 621 `pyproject.toml` (matching what `vendiqo_shared` already uses), is a single static binary that is trivial to add to Docker images (important for the ARM builds), and is supported by Dependabot. Poetry was rejected for its non-standard config dialect, slower resolver, and Docker boilerplate. pip-tools was rejected because it fixes only pinning, keeping the split `requirements*.txt` format and the manual shared-package install.

### 2. Independent projects, no uv workspace

Each of `cloud/backend`, `pi/backend`, `cloud/hosted-pi-manager` gets its own `pyproject.toml` + `uv.lock`. A root workspace (single shared lockfile) was rejected because:

- it couples cloud and pi dependency resolution, while pi ships as an independent device image;
- a root `uv.lock` would defeat the per-project CI path filters (`.github/filters.yaml`) — every dependency bump would trigger every backend pipeline;
- Dependabot's per-directory configuration maps 1:1 onto independent projects.

### 3. `vendiqo_shared` as an editable path source

`cloud/backend` and `pi/backend` declare `vendiqo-shared` as a dependency with `[tool.uv.sources] vendiqo-shared = { path = "../../packages/vendiqo_shared", editable = true }`. The relative path is recorded in the lockfile, so Dockerfiles must preserve the repo-relative layout inside the image (e.g. project at `/repo/cloud/backend`, shared package at `/repo/packages/vendiqo_shared`) instead of today's flat `/app` + `/packages` split.

### 4. Docker install pattern

Each backend Dockerfile pins the uv binary and installs from the lockfile only:

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:<pinned> /uv /usr/local/bin/uv
# copy pyproject.toml + uv.lock (+ vendiqo_shared) first for layer caching
RUN uv sync --frozen --no-dev
ENV PATH="/repo/<project>/.venv/bin:$PATH"
```

`--frozen` guarantees the lockfile is authoritative (build fails if out of sync); `--no-dev` keeps test tooling out of images. App code is copied after `uv sync` so dependency layers stay cached.

### 5. CI install pattern

`backend-tests.yml` and `openapi-sync.yml` use `astral-sh/setup-uv` (pinned, with cache enabled) and replace the pip steps with `uv sync --frozen` in the project directory, then `uv run python -m pytest ...`. The separate "Install shared package" step is dropped — the path source covers it. Python 3.12 is pinned via `requires-python` and a `.python-version` file per project, letting uv provision the interpreter.

### 6. Dependabot

The two `pip` entries switch to the `uv` package ecosystem (same directories), and a third entry is added for `/cloud/hosted-pi-manager`. Dependabot then updates `pyproject.toml` constraints and regenerates `uv.lock` in the same PR.

### 7. Ruff runs through uv (`uvx`)

`lint.yml` and `scripts/lint.sh` invoke ruff via `uvx ruff check ...` instead of `python -m pip install ruff` + `ruff check`. In CI the two ruff jobs use `astral-sh/setup-uv` and need no `setup-python`/pip step at all. Locally, `ruff_cmd` in `scripts/lint.sh` prefers `uvx ruff`, falling back to a `ruff` binary or `python3 -m ruff` if uv is not installed, and its error message points to installing uv. Ruff itself stays unpinned (matching today's behavior of always installing the latest); if rule-drift ever breaks CI, pinning is a one-line change (`uvx ruff@<version>`).

### 8. uv pinned at 0.11.29

The latest stable release as of this change (published 2026-07-15). uv is pre-1.0 and ships frequently, so pinning is the standard precaution. The pin appears in the four Dockerfiles (`ghcr.io/astral-sh/uv:0.11.29`) and in every `astral-sh/setup-uv` step (`version: "0.11.29"`).

## Risks / Trade-offs

- [First lock resolves current latest versions, effectively a mass upgrade of the unpinned deps] → run both backend test suites and the hosted-pi-manager suite against the new lockfiles before merging; pin back any package that breaks.
- ~~[`httpx2` in both `requirements-dev.txt` files is likely not the intended package]~~ → verified during implementation: `httpx2` is the pydantic-org successor to httpx and `starlette.testclient` imports it, so it is a required dev dependency. Kept.
- [Editable path dependency makes lockfiles layout-sensitive] → Dockerfiles replicate the repo-relative layout; CI runs from the repo checkout, which already matches.
- [Contributors without uv installed] → document one-line install in AGENTS.md/README; `uv sync` otherwise replaces multiple pip commands, so the workflow gets simpler, not harder.
- [`.github/filters.yaml` and workflow path triggers reference `requirements*.txt` indirectly via directory globs] → directory globs (`cloud/backend/**`) already cover the new files; verify no filter matches `requirements` explicitly.

## Migration Plan

Single PR, no runtime schema or API changes. Rollback = revert the PR (requirements files come back). Suggested order: convert `cloud/hosted-pi-manager` first (smallest, no shared package), then `pi/backend`, then `cloud/backend`, then CI/Dependabot/docs. Docker images rebuild from the same tags; no deployment coordination needed.

## Open Questions

None — the two previously open questions are resolved: ruff moves to `uvx` (Decision 7) and uv is pinned at 0.11.29 (Decision 8).
