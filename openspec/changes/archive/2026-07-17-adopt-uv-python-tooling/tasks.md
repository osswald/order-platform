## 1. Preparation

- [x] 1.1 Confirm 0.11.29 is still the latest stable uv release at implementation time; record the pin for Dockerfiles and `astral-sh/setup-uv` steps
- [x] 1.2 Investigate `httpx2` in `cloud/backend/requirements-dev.txt` and `pi/backend/requirements-dev.txt`; confirm whether anything imports it and decide drop/replace
- [x] 1.3 Snapshot currently installed versions per project (`pip freeze` from a clean install) as a reference for constraint choices

## 2. Convert cloud/hosted-pi-manager (smallest, no shared package)

- [x] 2.1 Create `cloud/hosted-pi-manager/pyproject.toml` (runtime deps + `dev` dependency group) and `.python-version` (3.12)
- [x] 2.2 Generate and commit `uv.lock`; run its test suite via `uv run python -m pytest tests/ -v`
- [x] 2.3 Update `cloud/hosted-pi-manager/Dockerfile` to pinned uv binary + `uv sync --frozen --no-dev`; verify image builds and starts
- [x] 2.4 Delete `cloud/hosted-pi-manager/requirements.txt` and `requirements-dev.txt`

## 3. Convert pi/backend

- [x] 3.1 Create `pi/backend/pyproject.toml` with `vendiqo-shared` as editable path source in `[tool.uv.sources]`, plus `.python-version`
- [x] 3.2 Generate and commit `uv.lock`; run tests via `uv run python -m pytest tests/ -v` (verify `vendiqo_shared` imports resolve)
- [x] 3.3 Update `pi/backend/Dockerfile` to uv install with repo-relative layout so the path source resolves; build for amd64 and arm64 locally (buildx) and verify startup
- [x] 3.4 Delete `pi/backend/requirements.txt` and `requirements-dev.txt`

## 4. Convert cloud/backend

- [x] 4.1 Create `cloud/backend/pyproject.toml` with `vendiqo-shared` path source, plus `.python-version`
- [x] 4.2 Generate and commit `uv.lock`; run tests via `uv run python -m pytest --cov=app --cov-fail-under=70`
- [x] 4.3 Update `cloud/backend/Dockerfile` and `Dockerfile.prod` to uv install with repo-relative layout; verify `docker compose -f cloud/docker-compose.yml up` works end to end
- [x] 4.4 Delete `cloud/backend/requirements.txt` and `requirements-dev.txt`

## 5. CI and automation

- [x] 5.1 Update `.github/workflows/backend-tests.yml`: replace setup-python/pip steps with pinned `astral-sh/setup-uv` (cache enabled) + `uv sync --frozen` + `uv run`; drop the separate "Install shared package" steps
- [x] 5.2 Update `.github/workflows/openapi-sync.yml` the same way (both jobs)
- [x] 5.3 Update `.github/dependabot.yml`: switch the two `pip` entries to `uv` and add `/cloud/hosted-pi-manager`
- [x] 5.4 Verify `.github/filters.yaml` and workflow path triggers cover the new files (directory globs) and reference no `requirements*.txt` explicitly
- [x] 5.5 Update `.github/workflows/lint.yml`: ruff jobs use pinned `astral-sh/setup-uv` + `uvx ruff check ...`; drop the setup-python and pip install steps
- [x] 5.6 Update `ruff_cmd` in `scripts/lint.sh` to prefer `uvx ruff`, keeping the `ruff` binary / `python3 -m ruff` fallbacks, and point the error message at installing uv

## 6. Documentation and verification

- [x] 6.1 Update `AGENTS.md`, `README.md`, and `cloud/README.md`: install/test commands become `uv sync` / `uv run pytest`, lint prerequisites reference uv instead of `pip install ruff`; add one-line uv install instructions
- [x] 6.2 Run `./scripts/lint.sh` and both backend test suites locally; confirm green
- [x] 6.3 Open PR and confirm all path-filtered CI jobs trigger and pass (backend tests, openapi-sync, pi-docker image build)
