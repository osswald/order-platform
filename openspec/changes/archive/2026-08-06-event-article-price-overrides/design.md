## Context

Catalogue articles today carry a single organisation-scoped `Article.price` (Float, major currency units). Events select which articles appear via stations and app layouts, and overlay stock via `EventArticleStock`. The edge bundle built by `article_snapshot_for_event` embeds `a.price` for every article (and addition) in the event set. Pi prices solely from that bundle field and snapshots `unit_cents` on sold lines.

Lager UI (`EventStockTab`) already lists the correct article universe — `event_stock_article_ids` (station/layout articles + linked additions) — grouped by station, with dirty autosave through `GET/PUT /events/{id}/event-stock`.

Organisations need sparse event-level sell-price overrides without duplicating articles or freezing prices at go-live.

## Goals / Non-Goals

**Goals:**

- Sparse per-event price overrides for every article in the Lager set (bases + additions).
- Same Lager tab: read-only Stammpreis + editable Eventpreis; clear input → inherit org price.
- Bundle and Pi always see effective price; no Pi schema change.
- Overrides editable throughout the event lifecycle.
- Event copy clones overrides for articles still in the new event’s allowed set.

**Non-Goals:**

- Separate price-list entities or shared “season” price books.
- Per-layout-cell or per-station prices (one price per article per event).
- Changing currency (remains on Organisation).
- Migrating catalog storage from Float major units to integer cents (leave as-is for parity with `Article.price`).
- Freezing / versioning prices when an event goes live.
- Changing historical sold-line prices (already snapshotted).

## Decisions

### 1. Storage: sparse `event_article_prices` table

- Columns: `event_id`, `article_id`, `price` (Float), unique `(event_id, article_id)`.
- Row present ⇒ override; absent ⇒ inherit `Article.price`.
- **Alternatives considered:** nullable column on `EventArticleStock` (couples money to stock lifecycle / lazy row creation); always-materialized price rows (heavier UX and copy). Sparse dedicated table matches “override only when set” and keeps stock upserts unchanged in spirit.

### 2. API: extend event-stock read/write

- Enrich each stock list item with `org_price` (from `Article.price`) and `price` (nullable override).
- PUT accepts optional `price` per item: number ⇒ upsert override; `null` / omitted-as-clear (explicit null) ⇒ delete override.
- Keep a single autosave payload so Lager remains one dirty surface.
- **Alternatives considered:** separate `/event-prices` endpoints (cleaner separation, worse UX sync); price-only PATCH (more round-trips). Extending stock wins because the article set and tab are shared.

### 3. Effective price merge in bundle snapshot

- In `article_snapshot_for_event` and `build_additions_for_base`, set `"price"` to `override ?? Article.price`.
- Load a price map for the event’s article ids (same pattern as `load_stock_map`).
- Bundle contract field stays `price: float`; semantics = effective sell price for that event.
- Bundle ETag / conditional GET naturally invalidates when overrides change (same assembly path).

### 4. Lager UI columns

- Add Stammpreis (formatted org money, read-only) and Eventpreis (numeric input).
- Empty / cleared Eventpreis maps to `price: null` on save → delete override.
- Show additions already in the stock list; no separate additions-only section.
- Reuse existing dirty autosave / `EventSaveStatusBar` wiring.

### 5. Lifecycle and copy

- No status gate: overrides writable whenever stock is writable for that event.
- `event_copy`: after configuration + stock clone, copy override rows for `article_id ∈ allowed` on the new event (same allowed-set logic as stock: additions / ingredients-aware membership).

### 6. Trust / fiscal

- Pi continues to recompute line prices from catalogue bundle on submit and snapshot `unit_cents`. Mid-event override changes affect new sales after the next successful catalogue pull; historical lines stay snapshotted.

## Risks / Trade-offs

- **[Risk] Org price changes while an override exists** → Mitigation: override wins until cleared; Stammpreis column always shows current org price so operators see drift.
- **[Risk] Clearing vs typing 0** → Mitigation: empty/null clears override; explicit `0` is a valid free/zero price if allowed by validation (match article price rules: non-negative).
- **[Risk] Stock PUT payload growth / partial clients** → Mitigation: treat missing `price` key as “leave override unchanged” only if needed for backward compat; prefer explicit null-to-clear from the updated UI that always sends the field. Document in OpenAPI.
- **[Risk] Reporting paths that fall back to live `Article.price` for unsapped lines** → Mitigation: out of scope to rewrite all reporting; new sales remain snapshotted. Note in tests that effective event price is what the bundle carries.
- **[Trade-off] Prices on the stock tab** → Couples two concerns in one view, but matches operator mental model (“this article at this event”) and avoids a second article list.

## Migration Plan

1. Schema patch: create `event_article_prices` (empty = no behaviour change).
2. Deploy backend that merges overrides (none yet) + extended stock API.
3. Deploy frontend Lager columns.
4. Rollback: drop reading overrides / ignore table; org prices remain correct. No data backfill required.

## Open Questions

- None blocking; confirm OpenAPI field semantics for PUT (`null` clears, number upserts) during implementation tests.
