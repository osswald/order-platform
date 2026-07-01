# AGENTS.md

## Cursor Cloud specific instructions

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

### Running tests

Install dev dependencies once per backend (`pytest`, `pytest-cov`):

- **Pi backend**: `cd pi/backend && pip install -r requirements.txt -r requirements-dev.txt && python3 -m pytest tests/ -v` (receipt rendering uses `python-escpos` + Pillow)
- **Cloud backend**: `cd cloud/backend && pip install -r requirements.txt -r requirements-dev.txt && python3 -m pytest tests/ -v`

With coverage report:

```bash
cd cloud/backend && pip install -r requirements.txt -r requirements-dev.txt && pytest --cov=app --cov-report=term-missing
cd pi/backend && pip install -r requirements.txt -r requirements-dev.txt && pytest --cov=app --cov-report=term-missing
```

CI runs both suites via `.github/workflows/backend-tests.yml` on changes under `cloud/backend/**` or `pi/backend/**`.

**Pi frontend**: `cd pi/frontend && npm ci && npm test` (Vitest; no Docker required)

**Cloud frontend**: `cd cloud/frontend && npm ci && npm test` (TypeScript; run `npm run typecheck` before build)

With coverage report:

```bash
cd pi/frontend && npm ci && npm run test:coverage
cd cloud/frontend && npm ci && npm run test:coverage
cd cloud/frontend && npm run typecheck
```

CI runs frontend tests via `.github/workflows/frontend-tests.yml` on changes under `cloud/frontend/**` or `pi/frontend/**`. Cloud PRs also run `npm run typecheck`. Backend schema changes trigger `.github/workflows/openapi-sync.yml`.

### Lint (Ruff + ESLint)

CI runs Ruff and ESLint via `.github/workflows/lint.yml`. Run the same checks locally before committing:

```bash
./scripts/install-git-hooks.sh   # once per clone: enables pre-commit lint on staged files
./scripts/lint.sh                # full lint (cloud + pi backends and frontends)
./scripts/lint.sh --staged       # lint only areas touched by staged files (what pre-commit runs)
npm run lint                     # same as ./scripts/lint.sh
```

Requires `python3 -m pip install ruff`, `npm ci` at repo root, and `npm ci` in `cloud/frontend` and `pi/frontend` before ESLint runs.

### Cloud frontend TypeScript and OpenAPI

The cloud frontend uses **strict TypeScript**, **openapi-fetch** (`src/api/client.ts`), and generated types from `cloud/frontend/openapi.json`.

When changing Pydantic schemas, routes, or response models under `cloud/backend/app/**`:

1. Run `python cloud/backend/scripts/export_openapi.py`
2. Run `cd cloud/frontend && npm run generate:api-types`
3. Commit updated `cloud/frontend/openapi.json` and `cloud/frontend/src/types/api.generated.ts` in the same PR

### Building frontends

- `cd cloud/frontend && npm run build`
- `cd pi/frontend && npm run build`

### Gotchas

- Docker runs inside a nested container (Firecracker VM). Requires `fuse-overlayfs` storage driver and `iptables-legacy`.
- Cloud backend auto-creates a bootstrap admin user and a default "Vendiqo" hire company on first start (via `apply_schema_patches()`).
- Pi PWA is designed to work unpaired (shows setup/pairing page). Pairing requires a cloud appliance credential.
- Stripe keys are optional for core functionality — leave `STRIPE_SECRET_KEY` empty for local dev.
