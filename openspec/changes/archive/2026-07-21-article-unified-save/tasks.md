## 1. Tests

- [x] 1.1 Add Vitest coverage for save orchestration decisions (which steps run on create vs edit; additions/ingredients applicability)
- [x] 1.2 Add failing tests for failure UX: when a later link step fails, overall result is failure with a step-identifying error (no overall success)
- [x] 1.3 Add failing tests for post-save destination: create resolves to new article detail id; update does not imply list navigation

## 2. Unified Save in Articles.vue

- [x] 2.1 Extract or implement orchestrated save (article create/update, then applicable additions/ingredients PUTs) using existing endpoints
- [x] 2.2 On create success, use returned article id and navigate to that detail (stay in detail mode); refresh list/catalog without `goToList()`
- [x] 2.3 On edit success, refresh list/catalog, keep detail open, show single success message
- [x] 2.4 On any step failure, stay on detail, show one comprehensible error for the failed step, do not show overall success
- [x] 2.5 Remove mid-page Save additions / Save ingredients buttons and nested success/error message UI wired only to those buttons

## 3. i18n and docs

- [x] 3.1 Add/adjust `en`/`de` article strings for unified success and step-specific save failures; remove unused nested-save labels if unused
- [x] 3.2 Update help copy under articles-and-categories if it implies separate saves for links

## 4. Verify

- [x] 4.1 Make orchestration tests pass against the implementation
- [x] 4.2 Run cloud frontend tests (`cd cloud/frontend && npm test`) and lint for touched areas
