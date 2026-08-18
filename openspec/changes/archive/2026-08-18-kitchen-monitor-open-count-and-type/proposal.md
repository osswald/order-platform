## Why

Kitchen staff scanning the Bestellungen board cannot see how many tickets are still open without counting cards, and table vs pickup is buried in title text next to a wait-time color language (green / amber / red bar). They need a backlog number in the title row and a glanceable type icon that does not look like urgency.

## What Changes

- Show the open-ticket count in the kitchen monitor **title row** next to the station label (e.g. `Grill · 8 offen`), including `0` when the board is empty
- Because the header is shared, the same count remains visible on Produkte
- On each Bestellungen ticket, show a table vs pickup icon at the **top right of the existing title line** (`mdi-table-chair` / `mdi-food-takeout-box`)
- Keep location text (`Tisch 12` / `Pickup A1`); icon is additive
- Color type icons sky (`#38bdf8`) for table and violet (`#c084fc`) for pickup — glyph only, not a second colored bar or chip
- Do **not** change ticket outer size, header padding, or column gap/width math
- No backend, API, or print-behavior changes

## Capabilities

### New Capabilities

- `kitchen-monitor-order-chrome`: Open-order count in the kitchen header title, and per-ticket table vs pickup type icons on Bestellungen cards

### Modified Capabilities

- None

## Impact

- `pi/frontend/src/components/kitchen/KitchenMonitorHeader.vue` (+ spec)
- `pi/frontend/src/views/KitchenMonitorView.vue` (pass `orders.length`)
- `pi/frontend/src/components/kitchen/KitchenTicketColumn.vue` (+ spec)
- Optional tiny `@mdi/js` dependency or inlined MDI paths on Pi frontend (Pi has no Vuetify/MDI today)
- No Pi/cloud backend, OpenAPI, or `kitchen-monitor-layout` density math changes
