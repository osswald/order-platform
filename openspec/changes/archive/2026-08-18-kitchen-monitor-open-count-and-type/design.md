## Context

See proposal.md — Why. The kitchen monitor header (`KitchenMonitorHeader.vue`) currently shows `{station} {event}` with no backlog count. Bestellungen tickets (`KitchenTicketColumn.vue`) already label location as `Tisch {n}` or `Pickup {code}` from `pickup_code` vs `table_number`, with wait time only on a 5px top bar (`#22c55e` / `#f59e0b` / `#ef4444`). Ticket header padding, `KITCHEN_ORDER_GAP_PX` (6), and `KITCHEN_MIN_COLUMN_WIDTH_PX` (200) are the density contract in `kitchen-monitor-layout`. Pi frontend has no MDI/Vuetify; admin screens use inline SVGs.

## Goals / Non-Goals

**Goals:**

- Pass `orders.length` into the header and render `{station} · {n} offen` in `.kitchen-title`
- Add a same-line type icon on each ticket without changing card chrome or column math
- Keep type vs wait as two visual channels (cool glyph vs warm bar)

**Non-Goals:**

- Backend / OpenAPI changes (tickets already carry `pickup_code` / `table_number`)
- Produkte card chrome (icons are Bestellungen-only)
- Splitting the header count into table vs pickup
- i18n extraction (kitchen copy is hardcoded German)
- Recoloring elapsed minutes or the urgency bar
- Changing print actions or polling

## Decisions

1. **Count lives next to the station label, not on the Bestellungen tab**  
   Form: `{stationLabel} · {n} offen` (including `n = 0`). Event name stays muted beside it.  
   **Why:** Matches the locked title-row choice; the header is already the glance target.  
   **Alternative:** Badge on the Bestellungen control — rejected after review.

2. **Count is `orders.length` from the existing kitchen poll**  
   Same list the board already shows; no extra query. Header is shared, so Produkte keeps the number.  
   **Alternative:** Count only while `viewMode === 'orders'` — rejected; hiding the backlog when switching views is worse.

3. **Type = pickup iff `pickup_code` is present, else table**  
   Same rule as `locationLabel()` today (pickup wins if both exist; missing table number still table).  
   **Alternative:** Infer from register vs waiter station — unnecessary; payload already distinguishes.

4. **Inline the two official MDI paths as SVG, no new Pi dependency**  
   `mdi-table-chair` and `mdi-food-takeout-box` path data in a small helper (or local constants), rendered as `currentColor` SVGs ~1.2rem on the title row. `aria-hidden` because the title text already names the type.  
   **Alternative:** Add `@mdi/js` to Pi — extra package for two icons.  
   **Alternative:** Pull Vuetify onto Pi — rejected.

5. **Icon sits in the existing title line via flex, not a new row or overlay chip**  
   Title block becomes `display: flex; justify-content: space-between; align-items: flex-start`. Icon `flex-shrink: 0`; title text `min-width: 0` with ellipsis if a long pickup code would collide. **Do not** change `.ticket-header` padding, `.ticket-column` radius/border, `--order-gap`, or `computeKitchenColumnLayout`.  
   **Alternative:** `position: absolute` overlay — can overlap title text.  
   **Alternative:** Colored pill/chip — reads as a second status badge next to the urgency bar.

6. **Glyph colors: table `#38bdf8`, pickup `#c084fc`**  
   Cool hues, equal saturation, not green/amber/red. No fill behind the icon. Elapsed text stays `--text`.  
   **Alternative:** Both muted grey (shape only) — deferred unless the hues feel loud in venue lighting.

## Risks / Trade-offs

- **[Risk] Extra `· n offen` wraps the tablet header** → Mitigation: keep it on the existing `.kitchen-title` flex row (`min-width: 0`, nowrap on the strong label); header already wraps controls.
- **[Risk] Long pickup codes collide with the icon** → Mitigation: title ellipsis + non-shrinking icon on the same line; do not grow padding.
- **[Risk] Sky/violet still read as “status” for color-blind cooks** → Mitigation: distinct MDI shapes; color is secondary.
- **[Trade-off] Produkte shows the open-ticket count** — accepted; it is the shared title row.

## Migration Plan

1. Ship Pi frontend only (header + ticket column + tests).
2. No data migration.
3. Rollback: revert the Vue/test change.
