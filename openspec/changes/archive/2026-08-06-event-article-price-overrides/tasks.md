## 1. Backend model and API tests

- [x] 1.1 Add failing tests for upsert/clear of event article price overrides and effective-price resolution (base + addition)
- [x] 1.2 Add failing tests for event-stock GET/PUT exposing `org_price` and nullable `price`, including clear-via-null
- [x] 1.3 Add failing tests that `article_snapshot_for_event` / addition nesting emit effective prices in the edge bundle
- [x] 1.4 Add failing tests that event copy clones overrides for allowed articles and skips orphans

## 2. Backend implementation

- [x] 2.1 Add `EventArticlePrice` model and schema patch for `event_article_prices`
- [x] 2.2 Implement load/upsert/delete helpers and wire into event-stock list/update schemas and routes
- [x] 2.3 Merge overrides in `article_snapshot_for_event` and addition price embedding (`build_additions_for_base`)
- [x] 2.4 Clone overrides in `event_copy` using the new event’s allowed Lager article set
- [x] 2.5 Run cloud backend tests and fix until green

## 3. OpenAPI and cloud frontend

- [x] 3.1 Export OpenAPI and regenerate cloud frontend API types
- [x] 3.2 Add failing frontend tests (or extend stock-tab coverage) for Stammpreis display, Eventpreis save, and clear → inherit
- [x] 3.3 Extend `EventStockTab` (types, headers, payload, i18n) with org price + override input
- [x] 3.4 Update help copy that implies a single global event price where needed
- [x] 3.5 Run cloud frontend tests/typecheck and fix until green

## 4. Verification

- [x] 4.1 Confirm Pi still prices from bundle `price` (add/adjust a regression assertion if cheap)
- [x] 4.2 Run relevant backend + frontend test suites and `./scripts/lint.sh` for touched areas
