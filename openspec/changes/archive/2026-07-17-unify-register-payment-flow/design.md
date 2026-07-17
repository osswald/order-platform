# Design: Unify Register Payment Flow

## Context

Today `POST /v1/orders` requires cash-register orders to carry payments matching the exact total; the order is born `paid`, pickup code and all print jobs are created inline, and the cash drawer kicks via `_create_payment_receipt` → `maybe_open_cash_drawer`. Waiter orders are born `open` and settled later through table/collective endpoints; `_settle_orders_partial` (edge_orders.py) already implements line-selection split settle with voucher redemption, receipt creation, and cloud sync, and is used by `settle_collective_partial`. On the frontend, `PayTableView.vue` and `PayCollectiveView.vue` are near-identical shells around `useSplitPay`.

## Goals / Non-Goals

**Goals:**
- Register orders created open, paid immediately after on a payment screen.
- Split payments, voucher redemption, and collective-bill assignment at the register, sharing the waiter implementation.
- Open register orders resumable from the register hub.
- Maximal reuse: one settle implementation on the backend, one split-pay screen on the frontend.

**Non-Goals:**
- Changing print timing (station slips, kitchen tickets, customer pickup slips stay at creation — confirmed decision).
- Gating pickup readiness on payment.
- Cloud backend/frontend changes.
- Removing the orphaned `POST /v1/orders/{id}/pay` / `PayOrderView` (left as-is).

## Decisions

1. **Order-scoped endpoints instead of pseudo-tables.** New `GET /v1/orders/{id}/summary`, `POST /v1/orders/{id}/settle-partial`, `POST /v1/orders/{id}/assign-collective` mirror the table endpoints but operate on the single register order. Alternative considered: treating each register order as a synthetic table number — rejected as hacky and colliding with the 1–99999 table range.
2. **Reuse `_settle_orders_partial` for register settlement.** The order settle route calls it with `[order]` and register context (`order_source`, `cash_register_uuid`, `cash_register_name`) in `settlement_meta`, so the existing receipt path kicks the cash drawer on cash payments with zero drawer-specific code. `settle_table_partial` (currently a ~200-line inline duplicate) is refactored onto the same helper, unifying table/collective/order settlement.
3. **Line-moving partial settles, pickup metadata stays on the original order.** Paid partials become new `LocalOrder` rows (as for tables); they carry register payment context in the payload but no `pickup_status`/`order_source` DB columns, so the pickup screen (filters on `order_source == "cash_register"` and `pickup_status in (pending, ready)`) only ever sees the original order. The original order's payload gets an `item_count` snapshot at creation so `_pickup_order_response` remains correct after lines move out.
4. **Payments at create stay supported.** If a register order arrives with payments (legacy clients, cloud-side flows), the current exact-amount + born-paid behavior is preserved. Only the empty-payments case changes to `open`. This keeps existing tests and sync consumers working.
5. **Voucher sales settle-in-full.** Voucher-sale lines are allowed on open register orders; because voucher slips must not print before payment, an order containing voucher-sale lines must be settled in one full payment, and the settle endpoint prints the voucher slips then. Alternative: pro-rata partial voucher sales — rejected as fiscally ambiguous.
6. **Whole-flow frontend reuse.** Extract `SplitPaySettleScreen.vue` from the two existing pay views; `PayTableView`, `PayCollectiveView`, and the new `RegisterPayView` become thin wrappers (summary/settle endpoints, actions-sheet config, fully-settled callback, optional TWINT-display hook). `PayTableActionsSheet` gains an `assignPath` prop and a `hideTransfer` flag instead of a register-specific clone.

## Risks / Trade-offs

- [Kitchen starts before payment; customer may walk away] → Confirmed product decision; open orders remain visible on the register hub for follow-up (settle or assign to collective bill).
- [Original register order can end up paid with empty lines after full partial settlement] → Same as tables today; pickup display uses the snapshotted `item_count` and DB pickup columns, cloud sync already handles line-moved orders.
- [Refactor of `settle_table_partial` could regress waiter settlement] → Existing table settle tests cover the behavior; refactor keeps the response shape identical.
- [Register orders assigned to a collective bill keep their pickup pipeline] → Intended: food prep is independent of who pays.

## Migration Plan

Pure feature branch; no schema migration (all new payload fields are additive JSON). Old Pi clients posting register orders with payments keep working.
