# Proposal: Unify Register Payment Flow

## Why

On the Pi, cash registers and waiters follow structurally different order processes: registers must collect payment before the order is created (`POST /v1/orders` rejects register orders without exact payments), while waiters create open orders and settle them later with split payments, voucher redemption, and collective-bill assignment. This duplication means registers cannot split payments, voucher redemption lives in a different place per role, and collective bills are waiter-only.

## What Changes

- Cash register orders are created with `payment_status = "open"` (no payments in the create call), then paid on a dedicated payment screen — same order-then-pay sequence as waiters.
- Registers gain split payments (per-line selection, multiple partial settlements) using the same settle machinery as tables and collective bills.
- Voucher redemption is removed from the register order screen (top menu) and is only available on the payment screen — the same placement as for waiters.
- Register orders can be assigned to a collective bill from the payment screen.
- Backing out of the payment screen leaves the order open; the register hub lists open orders so payment can be resumed.
- Kitchen/station slips, customer pickup slips, and pickup-code allocation remain at order creation (unchanged timing).
- Cash drawer kick moves with the payment: it fires when a cash payment is settled, not at order creation.

## Capabilities

### New Capabilities

- `register-order-settlement`: Order-scoped summary, partial/full settlement with split payments and voucher redemption, and collective-bill assignment for cash-register orders; open-orders listing per register.

### Modified Capabilities

<!-- No existing specs in openspec/specs/ cover order creation or payment; the only existing spec is event-stats-timestamp-parsing, which is unaffected. -->

## Impact

- Pi backend: `pi/backend/app/routers/edge_orders.py` (order creation validation, new order-scoped endpoints reusing `_settle_orders_partial`), `pi/backend/app/schemas/edge.py` (new response models), `pi/backend/app/routers/edge_common.py` (unchanged receipt/cash-drawer path now triggered at settle time for registers).
- Pi frontend: `RegisterOrderView.vue` (no payment/voucher step), new `RegisterPayView.vue` plus a shared split-pay screen extracted from `PayTableView.vue`/`PayCollectiveView.vue`, `RegisterHubView.vue` (open-orders list), router.
- Cloud sync: unchanged mechanism; register orders now sync first as open and are re-synced when settled (same as waiter orders today).
- No cloud backend/frontend changes.
