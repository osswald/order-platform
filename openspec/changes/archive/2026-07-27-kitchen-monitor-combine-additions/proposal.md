## Why

On the kitchen monitor **Produkte** view, additions are aggregated as orphan cards separate from their parent article. Kitchen staff then see e.g. Raclette and DOPPELT KÄSE as unrelated totals and cannot tell which addition belongs to which dish. Orders view already nests additions under the line; products view needs the same relationship when an addition is configured to combine.

## What Changes

- Add a per-link flag **Kombinieren auf Küchendisplay** on `article_addition_links` (same admin list as **Vorauswahl Pi**), so the same Zusatz can combine for one parent article and stay separate for another.
- Default the flag to **off** for existing links and for newly added links (opt-in).
- Sync the flag into the edge bundle on each base article’s `additions[]` entry.
- On the kitchen **Produkte** view: aggregate by parent + flagged additions (+ note); show product **label** on line 1, flagged additions on line 2, note on line 3; unflagged additions remain standalone product cards.
- On kitchen **Bestellungen** and **Produkte** views: prefer article/addition **label** over full **name** for shorter display text.
- **Remove** the Produkte-view **Zusätze** checkbox (and its localStorage preference); behaviour is driven only by the cloud link flags.

## Capabilities

### New Capabilities
- `kitchen-monitor-combine-additions`: Cloud per-link combine flag, edge bundle sync, and kitchen monitor products/orders display that folds flagged additions under the parent (with labels and notes)

### Modified Capabilities
- *(none — existing `kitchen-ticket-actions` / `pi-kitchen-monitor-routing` do not specify products-view aggregation or addition display)*

## Impact

- **Cloud backend**: `ArticleAdditionLink` column + schema patch/migration; additions API schemas; `build_additions_for_base` / replace-links; tests; OpenAPI export
- **Cloud frontend**: additions link table column next to Vorauswahl Pi; i18n; generated API types
- **Bundle contract / Pi**: `EdgeBundleArticleAddition` field; Pi SQLite bundle consumers
- **Pi frontend**: `buildKitchenProductSummary` aggregation + `KitchenProductList` / `KitchenTicketColumn` / header (remove Zusätze); prefer `label`; tests
- **Non-goals**: changing how addition qty is entered on the order sheet; printing/receipt layout; stock maths
