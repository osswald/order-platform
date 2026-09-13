## Why

Cash-register layouts use larger grids and benefit from one-tap sale of common variants (base article plus fixed Zusätze). Today a layout cell can only reference articles or vouchers; any article with additions always opens the Zusätze sheet, even when the operator always wants the same extras. That costs taps and slows register work.

## What Changes

- Layout cells MAY carry a locked set of additions for a single base article (predefined variant / combo button).
- On tap, a combo cell adds the cart line with those additions immediately — no Zusätze sheet, no post-tap editing.
- Combo cells are limited to exactly one article and no vouchers; multi-article cells and voucher cells keep today’s behaviour and cannot use locked additions.
- The grid disables a combo button when the base article or any locked Zusatz is not sellable / out of stock.
- Same behaviour on all layouts (waiter default and cash-register layouts).
- Cloud admin cell editor can configure locked Zusätze when the cell qualifies as a combo cell.
- Edge bundle / OpenAPI cell payloads include the locked addition ids; vouchers and article-level `preselected` (Vorauswahl Pi) are unchanged.

## Capabilities

### New Capabilities

- `layout-cell-locked-additions`: Configure and sell layout-cell predefined variants (one article + locked additions) with one-tap cart add and OOS-disabled buttons across Pi POS layouts.

### Modified Capabilities

- (none — existing sheet typography and voucher-cell behaviour stay as specified; this adds a new cell mode rather than changing those requirements)

## Impact

- **Cloud backend**: `LayoutCellIn` / `LayoutCellRead`, persistence for cell→locked addition links, event configuration validation, edge bundle serialization of layout cells.
- **Cloud frontend**: App-Layouts cell dialog — single-article + locked Zusätze UI; payload helpers; OpenAPI types after schema export.
- **Pi frontend**: `EventLayoutGrid` enablement for combo cells; waiter/register `beginAdd` / cell-pick path skips Zusätze sheet when the cell has locked additions; cart line already supports `additions[]`.
- **Shared**: `vendiqo_shared` bundle contract types for layout cells if present.
- **Tests**: Cloud config validation + Pi sellability/one-tap paths; regenerate OpenAPI types in the same PR as schema changes.
- **Out of scope**: Voucher behaviour; article-link `preselected` semantics; mandatory-addition rules; multi-article combo cells; editable-after-tap presets.
