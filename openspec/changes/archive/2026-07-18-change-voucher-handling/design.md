## Context

After unify-register-payment-flow, register orders create open and settle on a shared split-pay screen. Voucher sales were carved out: open register orders may contain `voucher_sale` lines, but settlement must cover the whole order, slips print only then, and assignment to a collective bill is rejected. Waiter create still raises `Gutscheinverkauf erfordert Zahlung` unless the order is born paid — so pay-later / non-instant waiter carts with vouchers fail even though the layout exposes sellable cells.

Line groups, selections, and line-move helpers key only on `article_id` and **skip** voucher-sale lines. Register pay treats vouchers as always-due `fixedRows`. Separately, `voucher_sale_unit_cents` trusts client `unit_cents` before looking up the definition, so a non-UI client can under/over-charge or sell unknown UUIDs when `unit_cents` is supplied.

Current voucher printing is network-only and register-oriented: jobs are queued against a cash-register receipt printer. Waiter Bluetooth printers are device-local (`window.AndroidPrinter` / SharedPreferences) and invisible to the Pi backend. Payment receipts already have a Bluetooth-vs-network destination prompt; station and voucher jobs do not.

## Goals / Non-Goals

**Goals:**
- Treat fixed-amount voucher-sale lines as settleable, movable open lines (split pay and collective assign), same as articles.
- Allow waiter open orders with voucher sales (pay-later and instant → collective).
- Print voucher slips when the order is submitted, at the same moment as station receipts.
- Route waiter voucher printing to the device Bluetooth printer when configured; otherwise ask which network printer to use.
- If no printer is available, warn and still allow order submission.
- Server-authoritative sale price from the event definition; reject invalid definitions.

**Non-Goals:**
- Unique voucher codes, balances, activation, or purchase↔redemption binding.
- Changing cloud voucher definition schema or slip visual layout (beyond correct print timing / destination).
- Allowing redemption credit to pay for voucher-sale face value (keep: credit applies to article gross only).
- Selling `article_entitlement` definitions (remain redemption-only).
- Registering waiter Bluetooth printers with the Pi backend or inventing a new device-claim print queue.
- Changing instant-mode accounting (instant orders remain born `paid` and attached to the instant collective).

## Decisions

1. **Voucher sales enter the shared line-group / selection model.**
   Extend summary line groups and `LineSelection` so a selection can identify either an article group or a voucher-sale group (`kind: "voucher_sale"` + `voucher_definition_uuid`, qty). Merge voucher rows into the same selectable list the UI already uses for split pay — remove register `fixedRows` / always-due behavior.
   - Alternative: separate `voucher_sale_selections` on settle bodies — rejected; doubles frontend/backend paths and breaks parity with table/collective screens.

2. **Reuse `_settle_orders_partial` / line-move for voucher units.**
   Teach take/merge helpers to move voucher-sale lines by definition UUID (qty split like articles). Remove the settle-in-full guard and the assign-collective hard reject. Settlement and assignment move already-issued voucher lines; they do **not** create additional voucher print jobs.

3. **Print vouchers at order submission, not at payment.**
   When an order containing voucher-sale lines is created successfully, print one slip per submitted voucher unit immediately — same transaction window as station receipt / kitchen ticket creation. Later partial settlement, full settlement, or collective assignment never reprints those units.
   - Accepted trade-off: an abandoned open order may leave printed vouchers in the world before payment. Product accepts this in exchange for waiter/register hand-out at sale time.
   - Instant mode keeps current semantics (born `paid`, parked on instant collective); vouchers still print at submit because that is create time.

4. **Waiter print destination: Bluetooth first, else ask.**
   Reuse the local Android printer bridge already used for payment receipts:
   - If the waiter device has a configured Bluetooth printer, print voucher ESC/POS there automatically after successful submit.
   - Else, before or as part of submit, prompt the waiter to choose a configured network printer target from the event bundle.
   - If neither Bluetooth nor any network target is available, show a warning and still submit the order (no blocking).
   Register orders continue to use the cash register’s configured receipt printer via the existing network print-job path (no Bluetooth picker on the register flow unless already present for receipts).

5. **Hybrid delivery model for waiter vouchers.**
   Because the backend cannot see Bluetooth printers, waiter voucher printing is frontend-driven after create:
   - Backend validates/prices lines, creates the order, creates station jobs as today, and returns printable voucher payloads (or a dedicated render endpoint) for the submitted voucher units.
   - Frontend sends those payloads to Bluetooth when configured, or creates / triggers network print jobs for the chosen printer.
   - Alternative: register waiter devices and claimable print jobs in Pi — rejected for this change as a larger schema/lifecycle project.

6. **Server-authoritative unit price.**
   Change `voucher_sale_unit_cents` to always resolve `voucher_definition_uuid` against the event bundle, require `fixed_amount`, and return definition `value_cents`. Ignore client `unit_cents` for pricing (still may snapshot the resolved value onto lines for fiscal display). Reject unknown UUID or non-sellable kind with 400.

7. **Payable amount.**
   Selected voucher-sale face value is part of the settlement gross alongside selected articles. Voucher **redemption** credit continues to reduce article gross only; it MUST NOT reduce voucher-sale totals.

8. **Summary API shape.**
   Prefer folding voucher sales into `line_groups` (with a discriminant) so table/collective/order summaries share one list. Keep or deprecate `voucher_sale_lines` as a transitional duplicate only if needed for old clients; Pi frontend will consume the unified groups.

## Risks / Trade-offs

- [Printed vouchers exist before payment] → Accepted product trade-off; open table/register/collective lists retain unpaid lines for follow-up.
- [Bluetooth print succeeds but network station print fails, or vice versa] → Keep existing station failure UX; surface voucher print failures distinctly where possible without blocking order creation.
- [No printer available] → Warn and continue; staff must handle manual/reprint follow-up outside this flow for now.
- [Selection schema change may break older Pi clients] → Additive fields + discriminant; deploy Pi backend and frontend together.
- [Ignoring client `unit_cents` surprises clients that relied on override] → No supported product need; document as intentional **BREAKING** semantics.
- [Double-print if settle also queues jobs] → Explicitly remove settle-time voucher job creation once submit-time printing is in place; cover with tests.

## Migration Plan

- Feature branch from `main`; primarily Pi behavioral change. Prefer no DB migration; if voucher print payloads need durable retry metadata, keep it additive JSON / existing print-job tables.
- Land backend + frontend (+ Android bridge usage) in one PR so submit-time destination logic and settle semantics ship together.
- Update/remove tests that expect full-settlement rejection, collective-assign rejection, and settle-time voucher printing.
- Rollback: revert PR; any open unpaid voucher orders created under the new build remain ordinary open lines.

## Open Questions

- None blocking. Default to warning-and-continue when no printer is available, as confirmed.
