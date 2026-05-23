# Order Platform Monorepo

Monorepo mit zwei Umgebungen:

- `cloud`:
  - `backend`: FastAPI + PostgreSQL
  - `frontend`: Vue.js / Vite
- `pi`:
- `pi/backend`: FastAPI + PostgreSQL + ESC/POS Druckerunterstützung
  - `frontend`: Vue.js / Vite

## Start

Für getrennte physische Deployments:

- Cloud-Server:
  - `docker compose -f cloud/docker-compose.yml up --build`
  - `http://localhost:8000`
  - `http://localhost:5173`
- Raspberry Pi:
  - `docker compose -f pi/docker-compose.yml up --build`
  - `http://localhost:8001`
  - `http://localhost:5174`

Für eine lokale Kombination beibehalten Sie `docker-compose.yml` im Projektstamm:

- `docker compose up --build`

- Cloud-Backend: `http://localhost:8000`
- Cloud-Frontend: `http://localhost:5173`
- Pi-Backend: `http://localhost:8001`
- Pi-Frontend: `http://localhost:5174`

## Struktur

- `cloud/backend`
- `cloud/frontend`
- `pi/backend`
- `pi/frontend`

## Notes

- Backends verbinden sich per Docker Compose mit eigenen PostgreSQL-Datenbanken.
- Frontends werden als Vite-Dev-Server gestartet.
