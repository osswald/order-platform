## Why

The cloud article detail page has three separate save actions (article, additions, ingredients). Operators reasonably expect one Save for the whole form; today the main Save can leave nested edits unsaved and then navigate away, causing lost work and confusion.

## What Changes

- Replace mid-page **Save additions** / **Save ingredients** buttons with a single primary **Save** that persists article fields and (when applicable) addition and ingredient links together.
- After a successful save (create or update), **stay on the article detail** instead of returning to the list so operators can continue editing nested sections.
- On any failure in the save sequence, treat the overall action as failed: stay on detail and show one comprehensible error message (no partial-success toast).
- **Back** remains the explicit way to return to the list (unchanged navigation intent).

## Capabilities

### New Capabilities

- `cloud-article-detail-save`: Cloud admin article detail save UX — unified persistence of article + links and post-save stay-on-detail behavior.

### Modified Capabilities

- (none)

## Impact

- **Cloud frontend:** `cloud/frontend/src/components/Articles.vue` (save orchestration, remove nested save buttons, post-create/update navigation), i18n strings under `articles.*` (remove or stop using nested save labels; add/adjust unified success/error copy), optional Vitest coverage for save orchestration helpers if extracted.
- **Cloud backend:** No API contract change required; continue using existing `POST/PUT /articles/`, `PUT /articles/{id}/additions`, `PUT /articles/{id}/ingredients`.
- **Pi / other services:** None.
