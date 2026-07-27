## Context

Kitchen monitor **Produkte** view (`buildKitchenProductSummary`) aggregates open ticket lines by parent `article_id` and, separately, by addition `article_id`. That produces useful prep totals but severs the parent↔modifier relationship (e.g. Raclette vs DOPPELT KÄSE).

**Bestellungen** already nests additions under each line (`kitchenLineAdditionLabels`) and shows notes. Article catalog already has short `label` (≤21) alongside `name`; the edge bundle already carries `label` on articles and addition entries. Addition links already store per-parent flags such as `preselected` (**Vorauswahl Pi**) on `article_addition_links`.

Constraints:

- Combine behaviour must be configurable **per base→addition link** (same Zusatz, different parents).
- Existing events must not suddenly split product cards until operators opt in.
- Prefer label on kitchen surfaces for shorter text; fall back to name when label is empty.

## Goals / Non-Goals

**Goals:**

- Persist and admin-edit `combine_on_kitchen_display` on each addition link (default **false**).
- Sync the flag in the edge bundle next to `preselected`.
- Products view: fold flagged additions into the parent card; keep unflagged additions as standalone cards; show label / additions / note lines; drop the Zusätze checkbox.
- Orders view: prefer labels for product and addition text (structure unchanged).

**Non-Goals:**

- Changing Pi addition picker qty UX (checkbox → always qty 1).
- Receipt / ESC/POS slip layout.
- Stock or pricing formula changes.
- A monitor-side “combine” or “Zusätze” toggle.

## Decisions

### 1. Flag on `article_addition_links`, not on the Zusatz article

- **Choice**: Boolean column `combine_on_kitchen_display` on `ArticleAdditionLink`, exposed in the same cloud additions table as **Vorauswahl Pi**.
- **Why**: Combinations differ per parent; matches existing link-scoped config pattern.
- **Alternative rejected**: Flag on `Article` (`is_addition`) — cannot differ per base article.

### 2. Default false for existing and new links

- **Choice**: Column `DEFAULT FALSE`; schema patch / migration leaves existing rows false; cloud UI defaults new rows to unchecked.
- **Why**: Opt-in avoids surprising card splits and lost orphan-prep totals until kitchen needs combine for that link.
- **Alternative rejected**: Default true / backfill true — would change live Produkte view for all orgs on deploy.

### 3. Products aggregation key

- **Choice**: Bucket open qty by:
  - parent article id
  - signature of **flagged** additions only (article_id + per-unit qty, sorted)
  - trimmed note
  Unflagged additions on a line still increment standalone addition buckets (by addition article id), and are omitted from the parent card’s addition line.
- **Why**: Notes must be their own line on the card, so they must participate in the key; mixing flagged/unflagged on one line still shows modifiers on the dish and sides as prep totals.
- **Alternative rejected**: Nested “davon …” under a single parent card — fights the Tisch/Stk matrix and hides variant differences.

### 4. Display lines and labels

- **Choice**:
  - Line 1: parent **label** (fallback name) + total qty
  - Line 2: flagged additions as `+ Nx <label>` (same shape as orders view)
  - Line 3: note when non-empty
  - Orders view and addition labels: prefer `label` over `name`
- **Why**: Matches explored UX; label is already the short kitchen-oriented field.

### 5. Remove Zusätze checkbox

- **Choice**: Delete header control + `pi_kitchen_show_additions_*` localStorage; products list always shows parent cards plus any standalone (unflagged) addition cards.
- **Why**: Cloud flags replace the view toggle; checkbox without combine was the orphan-addition problem.

### 6. Bundle field name

- **Choice**: `combine_on_kitchen_display: bool` on each `EdgeBundleArticleAddition` entry from `build_additions_for_base`.
- **Why**: Parallel to `preselected`; explicit name for kitchen consumers.
- Missing/undefined on older bundles → treat as **false**.

## Risks / Trade-offs

- **[Risk]** Orgs forget to enable the flag → kitchen still sees orphans for modifiers.  
  → **Mitigation**: Document in admin hint next to the column; default false is intentional opt-in.

- **[Risk]** Many note variants explode the products grid.  
  → **Mitigation**: Acceptable; notes are rare and already split lines in Bestellungen. Revisit only if operators complain.

- **[Risk]** Stale Pi bundles without the new field.  
  → **Mitigation**: Treat missing as false; behaviour matches pre-change until sync.

- **[Trade-off]** Combined mode loses a single global “how many DOPPELT KÄSE?” card for flagged links.  
  → Acceptable: that total was misleading without parent context; unflagged links keep standalone totals.

## Migration Plan

1. Add column with `DEFAULT FALSE` (Postgres + SQLite schema patches as used elsewhere for `preselected`).
2. Deploy cloud API + admin UI; regenerate OpenAPI / frontend types.
3. Deploy Pi frontend that reads the flag (missing → false) and new display rules.
4. Rollback: ignore unused column; Pi can temporarily ignore the field (false) if needed — no data backfill required.

## Open Questions

- *(none — defaults, flag placement, display lines, and Zusätze removal decided)*
