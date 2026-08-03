## Context

See `proposal.md` for motivation. Today `cloud/frontend/src/router/index.ts` statically imports every view; `main.ts` registers all Vuetify components/directives and pulls `@mdi/font` CSS; Help uses eager `import.meta.glob` for markdown. Several composables/views chain `await` on independent GETs. Waiters already expose `organisation_id` query filtering; other list APIs vary. `vite-plugin-vuetify` is already in `vite.config.ts`. Existing `event-configuration-perf` covers backend config summary loads — this design stays on the frontend shell and list UX.

## Goals / Non-Goals

**Goals:**
- Cut initial JS/CSS/font payload for authenticated navigation
- Lazy-load heavy routes and Help content
- Remove serial waterfalls on known hot mounts
- Prefer org-scoped list GETs where filters already exist

**Non-Goals:**
- Introducing Pinia or redesigning session architecture
- Migrating call sites to typed `openapi-fetch` helpers
- Adding server-side pagination for all catalogs (separate change if needed)
- Splitting god SFCs purely for maintainability
- Backend reporting SQL (see `cloud-busy-event-reporting`)

## Decisions

### 1. Vue Router dynamic imports for all authenticated feature routes

Use `() => import('...')` (and keep only tiny shared shells eager if needed, e.g. login). Group natural chunks: stats+charts, help+markdown, import wizard, large CRUD views.

**Alternatives considered:** `manualChunks` only without route lazy loading — still downloads unused route code on first hit to any authenticated page. Route lazy loading is the primary lever; optional `manualChunks` for vendor (vue, vuetify) can follow if measurements warrant.

### 2. Vuetify via plugin auto-import, not `import *`

Remove wholesale `components`/`directives` registration; keep `createVuetify({ locale, date, theme, defaults })` and rely on `vite-plugin-vuetify` to treeshake. Verify labs/date components still resolve (VDateInput note in `main.ts`).

**Alternatives considered:** Explicit allowlist of components — more brittle than the plugin already in the repo.

### 3. Icons via `@mdi/js` (or SVG paths) + Vuetify icon component

Replace `@mdi/font/css/materialdesignicons.css` with SVG icon set limited to used `mdi-*` names. Centralize a small icon map if that keeps templates clean.

**Alternatives considered:** Keep webfont but subset with a custom font build — heavier toolchain; SVG subset is simpler and matches Vuetify’s recommended modern path.

### 4. Parallelize with `Promise.all` / fire-and-forget where safe

Auth: only parallelize after access token/session is known. Articles: categories + articles + ingredients together when independent. Stats: parallelize articles/config with care for event-id dependency; stats fetch can start once event id is known from route params without waiting for full event GET if the stats API only needs `event_id`.

**Alternatives considered:** A global SWR library — higher scope; extend existing composable cache patterns (`useOrgCatalog`) only where lists already share data.

### 5. Org filter adoption is opportunistic, not a new pagination API

First consumers: APIs that already accept `organisation_id` (waiters confirmed). For events/articles, inspect existing query params (`minimal`, etc.) and use them if present; do not add **BREAKING** list pagination in this change.

## Risks / Trade-offs

- [Lazy route flash / layout shift] → Keep shared chrome in `App.vue`; use router view suspense or existing loading patterns; smoke-test mobile nav.
- [Vuetify auto-import misses a component] → Visual/regression pass on forms, dialogs, date pickers, data tables; fix by ensuring plugin scans SFCs.
- [Icon rename / missing glyph] → Script or test that lists template `mdi-*` against the shipped map.
- [Org-scoped fetch changes empty states] → Mirror today’s filtered empty behavior; add Vitest for waiters query param.

## Migration Plan

1. Land behind normal cloud frontend deploy (static assets).
2. No API migration required for MVP.
3. Rollback: revert frontend commit / prior image; no DB steps.
4. Measure before/after: `npm run build` chunk sizes and optional Lighthouse/network waterfall on dashboard.

## Open Questions

- Whether articles/events list endpoints already accept organisation filters worth wiring in the same PR, or only waiters in MVP.
- Whether EN locale lazy-loading is worth bundling into this change (proposal deferred it; can stay out).
