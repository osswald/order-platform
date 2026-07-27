## 1. Tests first (cloud)

- [x] 1.1 Extend addition-link unit/API tests for `combine_on_kitchen_display` round-trip, default false when omitted, and serialize/build_additions_for_base inclusion
- [x] 1.2 Add cloud frontend coverage (or component assertion) that the additions table exposes the new column next to Vorauswahl Pi

## 2. Cloud backend + admin

- [x] 2.1 Add `combine_on_kitchen_display` boolean on `ArticleAdditionLink` with DB default false (Postgres + SQLite schema patches mirroring `preselected`)
- [x] 2.2 Wire flag through Pydantic schemas, `replace_addition_links`, admin serialize, and `build_additions_for_base`
- [x] 2.3 Add cloud Articles additions-table column + i18n (de/en) + hint; default new link rows to false
- [x] 2.4 Export OpenAPI and regenerate `cloud/frontend` API types

## 3. Tests first (Pi kitchen)

- [x] 3.1 Extend `kitchenProductSummary` tests: flagged fold-in, unflagged standalone, mixed line, note splits buckets, missing flag → false
- [x] 3.2 Extend kitchen label/helpers tests: prefer `label` over `name` for parents and additions on orders + products paths
- [x] 3.3 Update header/product-list tests: Zusätze checkbox removed; standalone unflagged cards still render

## 4. Pi frontend

- [x] 4.1 Update bundle/shared types if needed so `EdgeBundleArticleAddition` includes `combine_on_kitchen_display`
- [x] 4.2 Implement combined aggregation + display fields in `buildKitchenProductSummary` (flagged signature + note key; separate unflagged buckets)
- [x] 4.3 Update `KitchenProductList` for label line 1, additions line 2, note line 3
- [x] 4.4 Prefer labels in Bestellungen (`KitchenTicketColumn` / `kitchenLineAdditionLabels`)
- [x] 4.5 Remove Zusätze checkbox, `showAdditions` state, and related localStorage from kitchen monitor header/view

## 5. Verification

- [x] 5.1 Run cloud backend addition tests, cloud frontend tests/typecheck as needed, Pi frontend kitchen tests
- [x] 5.2 Run `./scripts/lint.sh` for touched areas
