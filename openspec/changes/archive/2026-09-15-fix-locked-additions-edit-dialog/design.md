## Context

See `proposal.md` for why. The cloud App-Layouts cell editor already seeds `cellEdit.locked_addition_ids` from the layout cell when opening the dialog and loads Zusatz options via `/articles/{id}/additions`. A watcher on article tree selection + voucher uuids calls `clearLockedAdditionsUi()`, which zeros both options and selected ids whenever the cell looks non-combo. Unit tests stub `v-treeview`, so they miss production selection churn on dialog open.

Primary touchpoint: `cloud/frontend/src/components/EventConfigLayoutsSection.vue` (and its Vitest file). Backend replace/serialize paths are in scope only if a reopen test against a real GET proves ids never arrived.

## Goals / Non-Goals

**Goals:**

- Reopening a saved combo cell shows previously locked Zusätze as checked once options load.
- Clear locked ids only when the operator durably leaves combo eligibility (base article change, second article, or any voucher).
- Regression tests that exercise selection transitions after open (including empty → single article) without wiping seeded ids.

**Non-Goals:**

- Changing API shape, M2M persistence, or Pi one-tap combo behaviour.
- Redesigning the locked-Zusätze UX (still a checklist).
- Fixing unrelated layout-cell editor issues.

## Decisions

### 1. Clear locked ids only on intentional eligibility loss

**Choice:** Split “clear options / cancel in-flight fetch” from “clear selected locked ids”. On transient ineligible selection (e.g. empty tree while dialog is open), keep `cellEdit.locked_addition_ids` and only hide or idle the checklist. Clear selected ids when:

- article count becomes ≠ 1, or
- any voucher is selected, or
- the single base article id changes from a previous single-article selection.

**Alternatives considered:**

| Approach | Why not |
| --- | --- |
| Ignore watcher until tree finished loading | Fragile; other mid-dialog empties still wipe |
| Don’t clear ids inside `clearLockedAdditionsUi` ever | Would leave stale locks after intentional multi-article / voucher |
| Re-seed from cell on every watcher tick | Fights user edits mid-dialog |

### 2. Keep open-dialog seeding; don’t re-fetch cell just for display

**Choice:** Continue seeding from the in-memory layout cell (already merged from configuration GET). After options load, checkboxes use `includes(addition_article_id)` against the preserved id list. Optionally intersect with loaded option ids so orphaned ids don’t linger as invisible state—filter after options arrive, not before.

**Alternatives considered:** Re-GET configuration on every cell open — heavier and unnecessary if local cell already has ids after `loadLayoutCells` / apply.

### 3. Test strategy: drive the watcher, not only stubbed happy path

**Choice:** Extend `EventConfigLayoutsSection.spec.ts` to:

1. Open a cell with `locked_addition_ids: [20]` and assert ids remain after flush.
2. Simulate post-open selection going `[]` then back to `['art-10']` and assert ids still `[20]`.
3. Keep existing cases that clear on second article / voucher.

Optional manual check: reopen after save and confirm checks; Pi one-tap still works (persistence smoke).

## Risks / Trade-offs

- **[Risk]** Keeping ids during empty selection could briefly show a checklist with stale checks if UI still shows locked section — **Mitigation:** `showLockedAdditions` already gates on current selection; when hidden, ids sit inert until eligibility returns or intentional clear runs.
- **[Risk]** Orphaned locked ids if additions were unlinked from the article — **Mitigation:** after options load, filter `locked_addition_ids` to ids present in options (or leave them and let apply/normalize + backend validation handle); prefer filter-on-load for cleaner Apply payloads.
- **[Risk]** True save bugs misdiagnosed as UI — **Mitigation:** if a failing test shows cell/API already empty before open, stop and investigate PUT payload / merge; do not “fix” by hardcoding UI.

## Migration Plan

- Frontend-only deploy; no DB migration.
- Rollback: revert the Vue watcher/helper change; data already on server is unaffected.

## Open Questions

- None that block implementation. If manual reopen still shows empty after the watcher fix, investigate whether `mergeLayoutCellsFromResponse` / PUT omit ids (separate follow-up).
