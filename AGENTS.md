# AGENTS.md

## Cursor Cloud specific instructions

### Architecture overview

This is the **Vendiqo Order Platform** monorepo — a multi-tenant event/venue POS system with:

| Service | Stack | Port | Run command |
|---------|-------|------|-------------|
| Cloud Backend | FastAPI + PostgreSQL | :8000 | `docker compose -f cloud/docker-compose.yml up` |
| Cloud Frontend | Vue 3 / Vite | :5173 | `docker compose -f cloud/docker-compose.yml up` |
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

- **Pi backend** (all pass): `cd pi/backend && pip install -r requirements.txt && python3 -m pytest tests/ -v` (receipt rendering uses `python-escpos` + Pillow)
- **Cloud backend**: `cd cloud/backend && python3 -m pytest tests/ -v`
  - Known issue: the `test_security.py` rate-limit test exhausts the in-memory rate limiter quota, causing subsequent tests that call `/auth/token` to fail with 429. Run `test_security.py` separately or last.
  - Some event-status tests have pre-existing `hire_company_id NOT NULL` schema fixture issues.

### Building frontends

- `cd cloud/frontend && npm run build`
- `cd pi/frontend && npm run build`

### Gotchas

- Docker runs inside a nested container (Firecracker VM). Requires `fuse-overlayfs` storage driver and `iptables-legacy`.
- The passlib/bcrypt deprecation warning at startup is cosmetic and does not affect functionality.
- Cloud backend auto-creates a bootstrap admin user and a default "Vendiqo" hire company on first start (via `apply_schema_patches()`).
- Pi PWA is designed to work unpaired (shows setup/pairing page). Pairing requires a cloud appliance credential.
- Stripe keys are optional for core functionality — leave `STRIPE_SECRET_KEY` empty for local dev.
