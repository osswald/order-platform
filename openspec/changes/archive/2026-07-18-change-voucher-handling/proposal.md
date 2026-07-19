## Why

Voucher sales are treated as a special case that blocks normal POS settlement: voucher-containing orders must be paid in full, cannot move to a collective bill, and waiter paths reject unpaid voucher lines. That conflicts with how registers and waiters already settle food, and it leaves a backend pricing hole where clients can supply arbitrary `unit_cents`. Align voucher sales with ordinary line settlement and close the price bypass.

## What Changes

- Allow **partial / split settlement** of orders that include voucher-sale lines (pay some voucher units and/or some articles in one payment).
- Allow **assigning voucher-sale lines to a collective bill** (register and table flows).
- Allow **waiter sale of fixed-amount vouchers** on open table orders (pay-later and instant modes), not only cash-register orders.
- Print voucher slips when the order is submitted, alongside station receipts, rather than waiting for payment.
- On waiter devices, use the configured local Bluetooth printer automatically; otherwise ask the waiter to choose a network printer. If no printer is available, warn but allow submission.
- Print submitted voucher units only once; later split settlement or collective assignment does not reprint them.
- **BREAKING (API semantics):** reject client-controlled voucher sale prices — server always prices from the event voucher definition (`value_cents`); unknown or non-`fixed_amount` definitions are rejected.
- Remove the register-only “voucher orders must settle in full” and “cannot assign to collective” restrictions introduced with unify-register-payment-flow.

## Capabilities

### New Capabilities
- `voucher-sales`: Fixed-amount voucher sale lines as first-class order lines — creation from register and waiter, submission-time printer routing, split settlement and collective assignment, and server-authoritative unit pricing.

### Modified Capabilities
- `register-order-settlement`: Drop the requirement that voucher-sale orders must settle in full and the implied exclusion from collective assignment; voucher-sale lines follow the same split/assign semantics as other open lines.

## Impact

- **Pi backend:** `edge_orders.py` (create, settle-partial, assign-collective, table/collective settle), `vouchers.py` (`voucher_sale_unit_cents`), line-group / selection helpers in `edge_common.py` and line-move utilities, submission-time voucher rendering and explicit network-printer routing.
- **Pi frontend / Android:** Register and waiter order/pay UIs, local Bluetooth bridge integration, and network-printer selection — voucher sales become selectable settle rows and waiter submission performs destination-aware printing.
- **Tests:** Update `test_register_pay_flow.py`, `test_vouchers.py`, and related frontend settle/cart/printing tests; add waiter submission, printer fallback, and spoofed-`unit_cents` cases.
- **Cloud:** No definition-model change expected; sales still sync as order JSON. Reporting continues to scan voucher-sale lines.
- **Out of scope:** Issuing unique voucher codes/balances, linking redemption to a purchased instance, or changing slip layout beyond print-timing correctness.
