## Context

See `proposal.md` for motivation. Today an `EventAppLayoutCell` stores label/color, M2M `article_ids`, and voucher definition UUID(s). Pi `EventLayoutGrid` enables a cell when any sellable article or fixed voucher is present; waiter and register order views always open `AdditionsPickerSheet` when the chosen base article has linked additions. Article-link `preselected` only seeds that sheet. Cart lines already accept `additions: [{ article_id, qty }]`.

## Goals / Non-Goals

**Goals:**

- Persist locked addition article ids on layout cells and round-trip them through configuration API, edge bundle, and OpenAPI types.
- Admin can configure locked Zusätze only for valid combo cells (exactly one article, no vouchers).
- Pi one-tap path for combo cells on every layout; grid disables when base or any locked Zusatz is unsellable.
- Keep classic multi-article / voucher / sheet flows unchanged when `locked_addition_ids` is empty.

**Non-Goals:**

- Changing voucher sales, Vorauswahl Pi semantics, kitchen combine flags, or order-line pricing formulas.
- Per-device layout assignment for waiters.
- Qty other than 1 on locked additions in v1.
- Auto-generating button labels from locked additions.

## Decisions

### 1. Payload field: `locked_addition_ids: list[int]`

Ordered list of addition article ids on `LayoutCellIn` / `LayoutCellRead` and in the edge `app_layouts` cells. Empty list = classic cell.

**Alternative considered:** Nested objects `{ addition_article_id, qty }` — deferred; sheet and cart already use qty 1 for Zusätze.

### 2. Persistence: M2M association table (with sort order)

Mirror `event_app_layout_cell_articles` with something like `event_app_layout_cell_locked_additions (cell_id, article_id, sort_order)` so replace-on-save stays consistent with how cell articles are written in `event_config_validation.py`.

**Alternative considered:** JSON column on the cell — simpler migrate, weaker referential integrity and harder to query; rejected in favor of M2M + schema patch pattern already used for layouts.

### 3. Validation rules (cloud config save)

Reject (or clear with explicit error) when:

- `locked_addition_ids` non-empty and `len(article_ids) != 1`
- `locked_addition_ids` non-empty and any voucher UUID present on the cell
- Any locked id is not an `is_addition` article linked to that base via `ArticleAdditionLink`
- Locked id duplicates within the cell

Admin UI SHOULD prevent invalid combos; API remains the source of truth.

### 4. Combo detection on Pi

A cell is a combo cell iff `locked_addition_ids.length > 0` (and config already guarantees single article / no vouchers). Tap path: resolve the single article + build `additions` with `qty: 1` each → `addCartLine` → never open Zusätze sheet for that tap.

Classic path unchanged when the list is empty (including multi-article cells that later pick one article with additions).

### 5. Sellability / disable

Extend `cellEnabled` (or equivalent):

- Classic: existing rule (any sellable article or voucher).
- Combo: base article sellable **and** every locked addition sellable via the same `isAdditionSellable` / stock rules used by the Zusätze sheet.

If the base is sellable but a locked Zusatz is not, the whole button is disabled (variant unavailable).

### 6. Admin UX

In the layout cell dialog:

- When exactly one article is selected and no vouchers: show a checklist of that article’s linked Zusätze; selection writes `locked_addition_ids`.
- Selecting a second article or any voucher clears / hides locked additions and persists `[]`.
- Article tree may stay multi-select for classic cells; combo mode is simply “one article + optional locks.”

### 7. Shared behaviour

Waiter (`OrderView`) and register (`RegisterOrderView`) share the same grid + begin-add branching; no register-only flag.

### 8. OpenAPI / types

After schema change: export OpenAPI → regenerate cloud frontend types; update Pi local cell types / helpers to read `locked_addition_ids` from the bundle (default `[]` for older bundles).

## Risks / Trade-offs

- **[Stale links]** Locked addition removed from the base article’s additions list after config save → Mitigation: re-validate on configuration PUT; on Pi, treat missing/unlinked addition as unsellable and disable the button.
- **[Cart stock race]** Button enabled, then stock hits zero before submit → Mitigation: accept same race as today’s sheet confirm; order submit / stock checks already gate final acceptance.
- **[Import]** Orderjutsu layout import already drops addition product refs → Mitigation: leave import producing empty `locked_addition_ids`; no silent combo creation.
- **[Label clutter]** Operators must name variants themselves → Mitigation: acceptable; optional auto-label is a non-goal.

## Migration Plan

1. Schema patch: new association table; existing cells get no rows → empty locked set.
2. Deploy cloud API + admin UI accepting/emitting the field (default `[]`).
3. Deploy Pi that ignores unknown fields safely, then honors `locked_addition_ids`.
4. Rollback: stop writing locked ids; old Pi ignores the field; DB rows can remain harmlessly.

## Open Questions

None — qty=1, hard lock, disable-on-OOS, and layout-agnostic behaviour are decided.
