## Why

Cloud admin first paint and navigation feel slow because the production Vite build ships a single ~1.7 MB JS chunk (all routes, full Vuetify, Chart.js, help markdown, full MDI webfont) and several hot pages issue serial API waterfalls over full-collection list payloads. Fixing load shape and request parallelism improves perceived speed for every operator session without changing product behavior.

## What Changes

- Route-level code splitting: lazy-load cloud admin views (especially heavy ones: EventStats, Help, Orderjutsu import, EventConfiguration subgraph) instead of static imports in the router.
- Restore Vuetify tree-shaking: stop registering `import * as components/directives`; rely on `vite-plugin-vuetify` auto-import (already configured).
- Replace full `@mdi/font` webfont with an SVG / `@mdi/js` subset for the ~90 icons actually used.
- Parallelize known request waterfalls on auth bootstrap, Articles mount, and EventStats mount (and similar serial chains where independent).
- Use existing org-scoped list query params where the API already supports them (e.g. waiters `organisation_id`); prefer active-organisation fetches over tenant-wide `.all()` then client filter when straightforward.
- Defer Help markdown + `markdown-it` behind the Help route chunk.
- Keep response schemas and route URLs stable — no intentional **BREAKING** API changes. Optional query params for org scoping are additive.

## Capabilities

### New Capabilities
- `cloud-admin-ui-perf`: Cloud admin frontend load and navigation performance — code splitting, Vuetify/MDI payload, request parallelism, and org-scoped list fetching where APIs already allow it.

### Modified Capabilities
- (none — `event-configuration-perf` already covers backend config load/`fields=summary`; this change does not alter those requirements)

## Impact

- **Cloud frontend**: `src/main.ts`, `src/router/index.ts`, Vite build output, icon usage across components, list views (Events, Articles, Waiters, …), auth/session bootstrap composables, Help utilities.
- **Cloud backend**: Minimal or none for MVP (consume existing filters). Server-side pagination for catalogs is out of scope here.
- **Dependencies**: May add `@mdi/js` (or equivalent SVG icon path); may drop or stop importing `@mdi/font` CSS.
- **Tests**: Frontend Vitest for router lazy loading / icon helpers where practical; build-size smoke or documented bundle expectations; existing view tests updated for async components if needed.
- **Out of scope**: Pinia introduction, OpenAPI typed-client migration, god-component SFC splits for maintainability only, Pi frontend, edge ETag / reporting SQL (separate changes).
