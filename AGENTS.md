# AGENTS.md

## Cursor Cloud specific instructions

### Git workflow and releases

- Branch from `main`; land changes via pull request only.
- Do **not** bump [`VERSION`](VERSION) in feature PRs — add a `release:patch|minor|major` label instead.
- See [`docs/RELEASE.md`](docs/RELEASE.md) for branch protection, labels, and Pi image tags.

### Architecture overview

This is the **Vendiqo Order Platform** monorepo — a multi-tenant event/venue POS system with:

| Service | Stack | Port | Run command |
|---------|-------|------|-------------|
| Cloud Backend | FastAPI + PostgreSQL | :8000 | `docker compose -f cloud/docker-compose.yml up` |
| Cloud Frontend | Vue 3 / Vite / TypeScript | :5173 | `docker compose -f cloud/docker-compose.yml up` |
| Pi Backend | FastAPI + SQLite | :8001 | `docker compose -f pi/docker-compose.yml up` |
| Pi Frontend | Vue 3 / Vite PWA | :5174 | `docker compose -f pi/docker-compose.yml up` |

### Starting services

Docker must be running before starting stacks. Start dockerd if not already running:

```bash
sudo dockerd &>/tmp/dockerd.log &
sleep 2
sudo chmod 666 /var/run/docker.sock
```

Then start stacks:

```bash
cd /workspace/cloud && docker compose up -d --build
cd /workspace/pi && docker compose up -d --build
```

### Environment files

- `cloud/.env` — created from `cloud/.env.example`; dev defaults: `APP_ENV=development` (or omit), `POSTGRES_PASSWORD=devpass123`, `SECRET_KEY=devsecretkey123456789` (optional in dev), `ADMIN_EMAIL=admin@vendiqo.local`, `ADMIN_PASSWORD=admin123`, `ENABLE_OPENAPI=true`, `REFRESH_COOKIE_SECURE=false`. Production (`APP_ENV=production`) requires a strong unique `SECRET_KEY` (enforced at startup).
- `pi/.env` — created from `pi/.env.example`; set `SYNC_ENABLED=0` for local dev without cloud pairing; leave `ESCPOS_PRINTER_HOST_OVERRIDE` unset to print to cloud bundle printer IPs (or set it to a LAN printer IP)

### Node version (Cloud VM gotcha)

CI and the frontends target **Node 24** (Active LTS). Use Node 24 locally (`node -v` → `v24.x`) so typings, Vite, and Docker bases match. The Cloud VM may ship a different default `node` under `/exec-daemon/node`; install Node 24 via nvm and make it the default for login shells (prepended to `~/.bashrc`). Pi Swiss money-format tests accept ICU apostrophe variants for `de-CH` grouping, but staying on the supported major still avoids toolchain drift.

### Running tests

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) (install once: `curl -LsSf https://astral.sh/uv/install.sh | sh`). Each backend has a `pyproject.toml` + committed `uv.lock`; `uv sync` installs runtime and dev dependencies (including the editable `vendiqo_shared` path dependency):

- **Pi backend**: `cd pi/backend && uv sync && uv run python -m pytest tests/ -v` (receipt rendering uses `python-escpos` + Pillow)
- **Cloud backend**: `cd cloud/backend && uv sync && uv run python -m pytest tests/ -v`

With coverage report:

```bash
cd cloud/backend && uv sync && uv run pytest --cov=app --cov-report=term-missing
cd pi/backend && uv sync && uv run pytest --cov=app --cov-report=term-missing
```

When changing dependencies, use `uv add <pkg>` (or edit `pyproject.toml` and run `uv lock`) and commit `pyproject.toml` and `uv.lock` together.

CI runs both suites via `.github/workflows/backend-tests.yml` on changes under `cloud/backend/**` or `pi/backend/**`.

**Pi frontend**: `cd pi/frontend && ../../scripts/npm.sh ci && npm test` (Vitest; no Docker required)

**Cloud frontend**: `cd cloud/frontend && ../../scripts/npm.sh ci && npm test` (TypeScript; run `npm run typecheck` before build)

With coverage report:

```bash
cd pi/frontend && ../../scripts/npm.sh ci && npm run test:coverage
cd cloud/frontend && ../../scripts/npm.sh ci && npm run test:coverage
cd cloud/frontend && npm run typecheck
```

CI runs frontend tests via `.github/workflows/frontend-tests.yml` on changes under `cloud/frontend/**` or `pi/frontend/**`. Cloud PRs also run `npm run typecheck`. Backend schema changes trigger `.github/workflows/openapi-sync.yml`.

### OpenSpec (spec-driven changes)

The repo uses [OpenSpec](https://openspec.dev/) as a planning layer for non-trivial changes. Specs and change proposals live in [`openspec/`](openspec/) (`openspec/specs/` for living specs, `openspec/changes/` for in-flight changes); Cursor slash commands are generated in `.cursor/commands/` and `.cursor/skills/`.

Workflow: propose → review → apply → archive.

- `/opsx:propose "your idea"` — create a change proposal (proposal, tasks, spec deltas) for review before coding
- `/opsx:apply` — implement an approved change
- `/opsx:archive` — after merge, fold the spec deltas into `openspec/specs/` and archive the change
- `/opsx:explore`, `/opsx:update`, `/opsx:sync` — explore specs, update a change, re-sync specs

The CLI is a root dev dependency (`@fission-ai/openspec`), run it via `npx openspec` (e.g. `npx openspec list`, `npx openspec validate --all`). Project context for generated artifacts is configured in [`openspec/config.yaml`](openspec/config.yaml).

### Lint (Ruff + ESLint)

CI runs Ruff and ESLint via `.github/workflows/lint.yml`. Run the same checks locally before committing:

```bash
./scripts/install-git-hooks.sh   # once per clone: enables pre-commit lint on staged files
./scripts/lint.sh                # full lint (cloud + pi backends and frontends)
./scripts/lint.sh --staged       # lint only areas touched by staged files (what pre-commit runs)
npm run lint                     # same as ./scripts/lint.sh
```

Ruff runs via `uvx ruff` (requires uv; falls back to a `ruff` binary or `python3 -m ruff` if uv is missing). ESLint requires `./scripts/npm.sh ci` at repo root and in `cloud/frontend` and `pi/frontend` before it runs. Use `./scripts/npm.sh` instead of `npm` when installing dependencies to avoid the deprecated `devdir` config warning in some environments.

### Cloud frontend TypeScript and OpenAPI

The cloud frontend uses **strict TypeScript**, **openapi-fetch** (`src/api/client.ts`), and generated types from `cloud/frontend/openapi.json`.

When changing Pydantic schemas, routes, or response models under `cloud/backend/app/**`:

1. Run `python cloud/backend/scripts/export_openapi.py`
2. Run `cd cloud/frontend && npm run generate:api-types`
3. Commit updated `cloud/frontend/openapi.json` and `cloud/frontend/src/types/api.generated.ts` in the same PR

### Locale formatting (cloud only)

Numbers and dates in the cloud admin UI and PDFs use a shared resolution rule: **UI locale** (`de` / `en` from vue-i18n message keys) plus **organisation country code** (`CH`, `DE`, …) → format locale tag (`de-CH`, `de-DE`, …).

| Layer | Entry points | Library |
|-------|----------------|---------|
| Cloud backend | `cloud/backend/app/locale_format.py` | Python **Babel** (`format_decimal`, `format_datetime`) |
| Cloud frontend | `cloud/frontend/src/utils/money.ts`, `localeFormat.ts`, `formatLocale.ts` | **vue-i18n** `n()` / `d()` with `numberFormats` / `datetimeFormats` in `src/i18n/formats.ts` |

Money is always shown as **`{ISO currency} {amount}`** (e.g. `CHF 12.50`), not CLDR symbol placement. Pass `organisation_country_code` / `country_code` from API payloads into `formatMoney(..., currency, countryCode)`.

Contract tests in `cloud/shared/format-fixtures.json` are asserted by both `cloud/backend/tests/test_locale_format.py` and `cloud/frontend/src/utils/localeFormat.fixtures.test.ts`.

Pi backend/frontend formatting is **out of scope** for this stack; do not route Pi changes through Babel/vue-i18n formatters unless explicitly requested.

### Building frontends

- `cd cloud/frontend && npm run build`
- `cd pi/frontend && npm run build`

### Gotchas

- Docker runs inside a nested container (Firecracker VM). Requires `fuse-overlayfs` storage driver and `iptables-legacy`. On Docker 29+, `/etc/docker/daemon.json` must also disable the containerd snapshotter (`"features": { "containerd-snapshotter": false }`) for `fuse-overlayfs` to work.
- Cloud backend auto-creates a bootstrap admin user and a default "Vendiqo" hire company on first start (via `apply_schema_patches()`).
- Pi PWA is designed to work unpaired (shows setup/pairing page). Pairing requires a cloud appliance credential.
- Stripe keys are optional for core functionality — leave `STRIPE_SECRET_KEY` empty for local dev.
