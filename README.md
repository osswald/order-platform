# Order Platform Monorepo

Monorepo mit zwei Umgebungen:

- `cloud`:
  - `backend`: FastAPI + PostgreSQL
  - `frontend`: Vue.js / Vite
- `pi`:
  - `backend`: FastAPI + SQLite + ESC/POS Druckerunterstützung
  - `frontend`: Vue.js / Vite PWA
- `android`:
  - Native Android WebView-App für `pi/frontend`
  - Bluetooth-ESC/POS-Belegdruck für Kellnergeräte
- `packages/`:
  - `vendiqo_shared`: gemeinsame Python-Hilfsfunktionen (cloud + pi)
  - `frontend-shared`: gemeinsame Frontend-Utilities

Weitere Dokumentation: [cloud/README.md](cloud/README.md), [pi/README.md](pi/README.md), [AGENTS.md](AGENTS.md).

## Start

Für getrennte physische Deployments (zwei Terminals empfohlen):

- Cloud-Server:
  - `docker compose -f cloud/docker-compose.yml up --build`
  - Backend: `http://localhost:8000`
  - Frontend: `http://localhost:5173`
- Raspberry Pi / Edge:
  - `docker compose -f pi/docker-compose.yml up --build`
  - Backend: `http://localhost:8001`
  - Frontend: `http://localhost:5174`

Android-App (Debug/Emulator): lädt Pi-Frontend von `http://localhost:5174` (`adb reverse tcp:5174 tcp:5174`); API `http://localhost:8001`.

## Tests

Backend (pytest):

```bash
cd cloud/backend && pip install -r requirements.txt -r requirements-dev.txt && python3 -m pytest tests/ -v
cd pi/backend && pip install -r requirements.txt -r requirements-dev.txt && python3 -m pytest tests/ -v
```

Frontend (Vitest):

```bash
cd cloud/frontend && npm ci && npm test
cd pi/frontend && npm ci && npm test
```

Siehe [AGENTS.md](AGENTS.md) für Coverage-Befehle und CI-Details.

## Struktur

- `cloud/backend`
- `cloud/frontend`
- `pi/backend`
- `pi/frontend`
- `packages/vendiqo_shared`
- `packages/frontend-shared`
- `android`

## Konventionen

- Cloud-Backend nutzt PostgreSQL; Pi-Backend nutzt SQLite (lokal auf dem Gerät).
- DB-Schreibvorgänge in Routern nutzen `commit_or_raise()` (siehe `cloud/backend/app/db_errors.py`).
- FastAPI-Routen mit synchronem SQLAlchemy-Session-Zugriff sind `def` (nicht `async def`), damit kein Event-Loop blockiert wird.
- Gemeinsame Python-Logik (z. B. VAT-Split) liegt in `packages/vendiqo_shared` und wird von cloud/pi re-exportiert.
- Produktion: Alembic-Migration schlägt laut fehl — kein stilles `create_all`-Fallback (Cloud und Pi).
- Frontends werden als Vite-Dev-Server gestartet.
- Stripe Connect/Terminal Integrationspfad: `docs/stripe-connect-terminal.md`.

## Lockfiles

`cloud/backend/requirements.lock` und `pi/backend/requirements.lock` werden mit `pip-compile --generate-hashes --allow-unsafe` erzeugt (siehe Kommentar in den Lockfiles).
