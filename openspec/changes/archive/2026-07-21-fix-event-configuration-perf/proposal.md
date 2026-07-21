## Why

Event configuration GET/PUT for a real venue event takes ~27s for a ~4KB payload and often ends in a gateway **502** on save. The App-Layouts tab stays blank until a second full configuration load finishes, and the layout-cell article picker can appear empty because `/station-article-tree` shares the same overloaded loader and fails silently. Operators cannot reliably edit layouts or persist changes.

## What Changes

- Replace multi-collection `joinedload` graphs in event configuration loading with `selectinload` (or equivalent non-cartesian loading) so GET/PUT complete in seconds, not tens of seconds.
- Avoid a second full heavy reload on PUT where practical; keep response shape compatible (`EventConfigurationRead`).
- Stop the layouts tab from re-fetching the entire configuration solely for cells when a lighter path exists (cells-aware load or reuse of already-loaded data).
- Make the layout-cell article tree resilient: surface load errors / empty states; prefer building the picker from station article IDs already known to the client (or a lean tree endpoint that does not reload the full config graph).
- Add regression coverage for loader strategy and for UI empty/error states on the cell article tree.

No **BREAKING** API contract changes intended: same routes and response schemas; performance and reliability only.

## Capabilities

### New Capabilities

- `event-configuration-perf`: Performance and reliability requirements for reading/writing event configuration and the station-article tree used by layout cell editing.

### Modified Capabilities

- (none)

## Impact

- **Cloud backend:** `get_event_for_configuration` / callers in `events_helpers.py`, `events_configuration.py`, `build_station_article_tree`, possibly mirrored load patterns in `edge.py` / `event_copy.py` if in scope for the same bug class.
- **Cloud frontend:** `EventConfigLayoutsSection.vue` (layout cells load + cell dialog tree), optionally `EventConfiguration.vue` (autosave / persist path).
- **Ops:** Fewer Caddy 502s on config save; App-Layouts tab usable without multi-ten-second waits.
- **Tests:** Backend load/query or behavioral tests; frontend Vitest for tree empty/error handling.
