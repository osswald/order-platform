## Context

`Articles.vue` presents one detail form but persists through three endpoints:

1. `POST /articles/` or `PUT /articles/{id}` — core fields  
2. `PUT /articles/{id}/additions` — addition links (edit mode, non-addition articles only)  
3. `PUT /articles/{id}/ingredients` — ingredient links (edit mode, when org ingredients are enabled)

Each nested section has its own save button and message. Main Save currently calls `goToList()` after success, discarding any unsaved nested local state. Additions/ingredients UI only appears once an article id exists (`editMode && activeId`).

Stakeholders: cloud admin operators maintaining the catalogue.

## Goals / Non-Goals

**Goals:**

- One primary Save on the article detail form.
- Save orchestrates article + applicable link resources.
- Successful create/update keeps the user on detail (create navigates to the new article’s detail).
- Failed orchestration shows one clear error and stays on detail; no success messaging for a partial sequence.
- Remove mid-page Save additions / Save ingredients controls.

**Non-Goals:**

- New backend composite/transactional endpoint for atomic multi-resource write.
- Dirty tracking / leave-guards / autosave (can be a follow-up).
- Changing list/detail routing model beyond post-save destination.
- Pi frontend or sync behavior.

## Decisions

### 1. Client-side orchestration (no new API)

**Choice:** Keep the three existing endpoints; frontend `saveArticle` (or a renamed orchestrator) sequences them.

**Why:** Meets UX goals without OpenAPI/schema churn. Endpoints already support full replace of link sets via PUT.

**Alternatives considered:** Single transactional backend endpoint — better true atomicity, deferred as non-goal.

### 2. Save sequence

**Choice:**

```
validate form
→ create or update article
→ if create: goToDetail(newId), refresh list/catalog, load empty link sections as today
→ if edit and additions section applies: PUT additions
→ if edit and ingredients section applies: PUT ingredients
→ show single success message; stay on detail
```

On **create**, nested sections were not editable yet, so only the article POST runs, then stay on the new detail (sections become available for the next Save).

On **edit**, always persist currently applicable link payloads from local state (even if unchanged) so one Save is authoritative — same as today’s dedicated buttons.

**Alternatives considered:** Skip unchanged link PUTs via dirty flags — deferred (non-goal); always PUT is simpler and matches current button semantics.

### 3. Failure semantics (“fail whole action”)

**Choice:** Overall Save succeeds only if every intended step succeeds. If any step fails:

- Do not show a success toast/message for the overall action.
- Stay on detail.
- Show one comprehensible error naming what failed (e.g. article vs additions vs ingredients), using API error text when available.
- Leave local form/link state intact so the operator can fix and retry.

**Caveat (accepted):** Without a transactional API, an earlier step may already be persisted when a later step fails (e.g. article updated, ingredients PUT failed). The UI must not claim full success; messaging should make the failed step clear so retry is obvious. True rollback is out of scope.

**Alternatives considered:** Roll back previous steps client-side — fragile and incomplete for updates; rejected.

### 4. Post-save navigation

**Choice:** Never call `goToList()` on successful Save. Create uses returned `ArticleRead.id` then `goToDetail(id)`. Update refreshes list data in the background but keeps the detail open. **Back** (and delete-when-viewing) still leave as today.

**Why:** Matches product decision; enables immediate linking after create.

### 5. Messaging UI

**Choice:** Continue using the existing inline `message` / `messageType` pattern on the form (consistent with other cloud admin entities). Collapse nested `additionsMessage` / `ingredientsMessage` into the single form message for Save outcomes. Prefer clear i18n keys for orchestrated failures.

**Alternatives considered:** Introduce a global snackbar — inconsistent with Articles and siblings; skip for this change.

### 6. Tests-first

**Choice:** Prefer extracting pure orchestration helpers (sequence decision + which steps run + error classification) with Vitest, or component tests if the project already tests Articles that way. At minimum, cover: create stays on detail path; edit runs link PUTs when sections apply; failure after article step surfaces failed-step message and does not treat as success.

## Risks / Trade-offs

- **[Risk] Partial persistence on mid-sequence failure** → Mitigation: clear failed-step error; stay on detail; retry-safe local state; document as accepted limitation in this change.
- **[Risk] Create then immediate Back loses chance to add links** → Mitigation: expected; operator can reopen from list; same as needing a second visit today after create→list.
- **[Risk] Always PUT links on every edit Save increases traffic** → Mitigation: payloads are small; dirty optimization deferred.
- **[Trade-off] No atomic DB transaction** vs faster ship without backend work — accepted for this UX-focused change.

## Migration Plan

- Frontend-only deploy; no data migration.
- Rollback: revert Articles.vue + locale keys.
- Help copy: optionally note one Save persists links (low priority; update `articles-and-categories` help if it mentions separate saves).

## Open Questions

- None remaining for this change (stay on detail; fail-whole UX messaging; create stays on detail; link-only edit frequency not relevant).
