## 1. Backend loader tests

- [x] 1.1 Add a regression test that `get_event_for_configuration` loads stations, layout cells, and related collections correctly for a multi-collection fixture (stations with articles, layout cells with articles, waiters, registers, vouchers)
- [x] 1.2 Assert the configuration load path uses `selectinload` for collections (or otherwise does not stack multi-collection `joinedload`s)—e.g. inspect query options or document via a focused helper unit test
- [x] 1.3 Add/extend API test: GET full configuration and GET `?fields=summary` still match existing response contracts
- [x] 1.4 Add/extend API test: PUT configuration returns 200 with `EventConfigurationRead` for a fixture with layout cells and station articles

## 2. Backend implementation

- [x] 2.1 Rewrite `get_event_for_configuration` collection loads to `selectinload` (stations→articles, stations→printer_rules, layouts→cells→articles when included, waiters, cash registers, voucher definitions, kitchen monitors)
- [x] 2.2 Slim `/station-article-tree` so it does not load the full configuration graph (stations→articles only, or dedicated ID query) before `build_station_article_tree`
- [x] 2.3 Confirm PUT path still reloads via the efficient helper after commit; remove any redundant expensive reload if present
- [x] 2.4 Run cloud backend pytest suite and fix regressions

## 3. Frontend tree / layouts UX tests

- [x] 3.1 Add Vitest coverage for layout cell article picker: empty state when no station articles; error state when tree load fails (no silent swallow)
- [x] 3.2 Add/adjust test that picker can render articles from station assignments (client-built tree and/or successful API nodes)

## 4. Frontend implementation

- [x] 4.1 Stop swallowing station-article-tree errors in `EventConfigLayoutsSection`; show error + keep filter/empty messaging
- [x] 4.2 Build cell article tree from parent station article union + org catalog when available (reuse `buildArticleCategoryTree` / `mapTreeNodes`); keep API fetch as fallback or remove if redundant
- [x] 4.3 Wire props from `EventConfiguration.vue` (`stationsLocal` / event article catalog) into the layouts section as needed
- [x] 4.4 Run cloud frontend Vitest (and typecheck if types changed)

## 5. Verify

- [x] 5.1 Manually or via timing notes: configuration GET/PUT for a multi-station event completes in low single-digit seconds locally against Postgres when available
- [x] 5.2 Run `./scripts/lint.sh` on touched areas
- [x] 5.3 Confirm OpenAPI/types unchanged unless a new query param or endpoint was added (regenerate only if needed)
