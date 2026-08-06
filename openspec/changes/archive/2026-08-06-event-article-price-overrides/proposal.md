## Why

Organisations sell the same catalogue articles at different prices depending on the event (e.g. club night vs festival), but today each article has a single organisation-level price. Staff must either live with the wrong price, maintain duplicate articles, or rely on ad-hoc discounts — none of which preserve a clean shared catalogue with event-specific sell prices.

## What Changes

- Add sparse **per-event article price overrides**: org `Article.price` remains the default; an event may optionally override price for any article in its Lager set (stations/layouts + linked additions).
- Extend the existing **Lager** event tab to show Stammpreis (read-only org price) and an Eventpreis override input; clearing the input removes the override and reverts to the article price.
- Overrides remain editable for the full event lifecycle (not frozen at go-live).
- Edge catalogue bundle snapshots emit the **effective** price (`override ?? Article.price`) so Pi POS and fiscal snapshots need no new schema.
- Event copy clones price overrides for articles that remain in the new event’s allowed set (same pattern as stock).
- Help/docs wording that implies a single global price for events is updated.

## Capabilities

### New Capabilities

- `event-article-price-overrides`: Sparse event-scoped sell prices for catalogue articles (including additions), Lager UI, bundle effective price, and event-copy behaviour.

### Modified Capabilities

- (none — no existing living spec covers event stock/Lager pricing; edge bundle price semantics are introduced here as part of the new capability)

## Impact

- **Cloud backend**: new `EventArticlePrice` (or equivalent) model + schema patches; extend event-stock list/update API (or adjacent endpoints) to read/write overrides; merge into `article_snapshot_for_event` / addition price embedding; `event_copy` clones overrides.
- **Cloud frontend**: `EventStockTab` columns + payload; i18n; OpenAPI type regen after schema export.
- **Shared bundle contract**: still `price: float` on articles — meaning becomes effective event price (document in contract/comments if needed).
- **Pi backend/frontend**: no structural change if they already price from bundle `articles[].price`; regression coverage that overrides appear after sync.
- **Tests**: cloud stock/price API, snapshot merge, event copy; frontend stock tab behaviour; optional Pi bundle pricing assertion.
