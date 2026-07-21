## Context

Cloud event configuration is loaded via `get_event_for_configuration` in `cloud/backend/app/routers/events_helpers.py`, which stacks many collection `joinedload`s (stations→articles, stations→printer_rules, layouts→cells→articles, waiters, registers, vouchers, kitchen monitors). SQLAlchemy then emits a single JOIN with a cartesian product. On a real venue event (~3 stations, ~28 station articles, ~12 layout cells), GET `/events/{id}/configuration` measured ~27s for ~4KB JSON.

The frontend compounds this:

1. Initial load uses `?fields=summary` (no cells).
2. Opening **App-Layouts** mounts `EventConfigLayoutsSection`, which GETs the **full** configuration again and hides the grid until done.
3. Opening a layout cell GETs `/station-article-tree`, which also calls `get_event_for_configuration` (full graph), then builds a category tree. Errors are swallowed (`/* tree optional */`), so timeouts look like “no articles.”
4. PUT `/configuration` loads the full graph, replaces children, commits, then loads the full graph **again** for the response — often exceeding Caddy’s upstream timeout → **502**.

Stakeholders: venue operators editing event config; platform maintainers (gateway 502 noise).

## Goals / Non-Goals

**Goals:**

- Configuration GET (summary and full) and PUT complete well under typical reverse-proxy timeouts (target: low single-digit seconds for venue-sized events on production Postgres).
- App-Layouts grid appears promptly after navigating to the tab.
- Layout-cell article picker shows station articles reliably when stations have articles; shows an explicit empty or error state otherwise.
- Preserve existing API shapes (`EventConfigurationRead`, station-article-tree `{ nodes }`).

**Non-Goals:**

- Redesigning layout/station UX or voucher rules.
- Broad rewrite of edge sync loaders (optional follow-up if the same `joinedload` pattern appears there).
- Changing Caddy timeout as the primary fix.
- Caching configuration in Redis or similar.

## Decisions

### 1. Use `selectinload` for configuration relationship graphs

**Choice:** In `get_event_for_configuration`, replace collection `joinedload` chains with `selectinload` (nested `selectinload` for stations→articles, layouts→cells→articles, etc.). Keep `joinedload(Event.organisation)` if it remains a many-to-one.

**Why:** Avoids cartesian JOIN explosion while keeping eager loading (no N+1 on serialize).

**Alternatives considered:**

- Manual ID queries + dict assembly — more code, easy to drift from ORM relationships.
- Raise Caddy timeout only — masks the bug; still burns DB/CPU.
- Drop eager loading entirely — risks N+1 on serialize loops.

### 2. PUT response: one efficient reload (not two expensive ones)

**Choice:** After commit, reload with the same selectinload helper (single pass). Optionally reuse the in-memory event after `expire`/`refresh` only if tests prove equivalence; prefer an explicit second `get_event_for_configuration` that is now cheap.

**Why:** Response must stay `EventConfigurationRead`. The bug is cost of load, not that a reload exists.

**Alternatives considered:**

- Return 204 / omit body — **BREAKING** for frontend autosave that reads `printer_options`.
- Build response from the PUT payload without DB reload — can miss server-normalized fields / sort orders.

### 3. Leaner station-article-tree path

**Choice (preferred):** Implement `build_station_article_tree` against a **minimal** event load (stations→articles only, or a dedicated query for station article IDs + org categories), not the full configuration graph.

**Frontend (complementary):** Pass station article IDs + org article catalog into the layouts section (parent already has `stationsLocal` and `stationArticleCatalog` / `eventArticleCatalog`) and build the selectable tree client-side with existing `buildArticleCategoryTree` / `mapTreeNodes`. Keep the API endpoint for other callers / consistency, but stop depending on a full config load for the dialog.

**Why:** Matches how vouchers already use `eventArticleCatalog`; removes a full-graph GET from the critical cell-edit path.

### 4. Layout cells loading

**Choice:** Prefer one of:

- **A (minimal):** Keep full GET for cells but with selectinload so it is fast enough; or  
- **B (better UX):** Add `?fields=cells` / dedicated cells endpoint, or have the initial configuration load include cells when the layouts tab is likely needed.

**Decision for this change:** Start with **A** (selectinload makes the existing second GET acceptable). If still sluggish or wasteful, add a cells-only query in the same PR if cheap; otherwise defer to a follow-up.

**Also:** Surface tree load errors; empty state when `nodes` is empty and stations have no articles.

### 5. Scope of selectinload rollout

**In scope:** `get_event_for_configuration` (all configuration GET/PUT/tree callers using it).

**Same PR if trivial:** Identical stacked `joinedload` in `edge.py` / `event_copy.py` only if touched or clearly the same footgun for production; otherwise note as follow-up — edge payloads can be larger and benefit, but this change is driven by admin config UX.

## Risks / Trade-offs

- **[Risk] selectinload increases query count** → Mitigation: still O(collections), not O(cartesian rows); measure with a fixture shaped like the venue event.
- **[Risk] Client-side tree drifts from server validation** → Mitigation: server still enforces `assert_cell_articles_subset_of_stations` on PUT; client uses the same station union already used for vouchers.
- **[Risk] PUT already committed when client sees 502** → Mitigation: speeding the response is the fix; document that operators may hard-refresh after a historical 502.
- **[Risk] Tests only use tiny SQLite fixtures and miss the regression** → Mitigation: add a unit/integration assertion on loader options (selectinload present / no multi-collection joinedload) and/or a scaled fixture with multiple collections.

## Migration Plan

1. Land backend loader change behind normal deploy (no schema migration).
2. Deploy frontend empty/error + optional client-side tree in the same release if possible so UX improves together.
3. Rollback: revert PR; no DB rollback needed.

## Open Questions

- None blocking: prefer client-side tree from parent catalog **and** lean backend tree endpoint; implement both if time allows, backend lean load at minimum.
