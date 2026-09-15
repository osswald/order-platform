## Why

When a SumUp connected card payment fails or is declined, the Pi POS only shows a brief toast and leaves operators without a clear path to retry or switch method. Once a checkout is waiting for the card, operators also cannot cancel from Vendiqo even though terminate already exists on the edge API and in the living `sumup-cloud-payments` spec. Overlapping green-check taps during the wait can also leave split-pay looking like there is “nothing to settle” after a reported failure.

## What Changes

- Show a **full-screen / sheet failure message** on the Pi POS when a `sumup_connected` attempt fails, is declined, times out, or is otherwise unsuccessful (not toast-only).
- Add **Abbrechen** on the shared SumUp waiting UI so operators can cancel an in-progress connected checkout from every place `sumup_connected` is offered (register, table, collective, legacy order pay).
- On cancel: best-effort terminate on the reader, keep the order unpaid, return quietly to the settle/pay screen (same pattern as Twint cancel).
- On failure dismiss: return to settle/pay so the operator can tap pay again and choose the same or a different method (no auto-restart of SumUp).
- Harden races: lock pay for the entire SumUp collection window; never settle an attempt the operator cancelled; ignore late `paid` for a cancelled attempt.
- **Pi only** — no cloud admin UI changes; reuse existing edge terminate/status APIs.

## Capabilities

### New Capabilities

- `sumup-connected-payment-ux`: Pi POS operator UX for in-progress SumUp connected payments — waiting UI with cancel, prominent failure surfacing, retry/other-method return path, and attempt-scoped settle guards against double-submit and late success after cancel.

### Modified Capabilities

- `sumup-cloud-payments`: Clarify that terminate MUST be reachable from the POS waiting UI (not only backend capability), and that failed/cancelled attempts MUST leave the order unpaid and MUST NOT record a payment for that attempt.
- `register-order-settlement`: Register (and shared split-pay) settlement MUST keep open unpaid lines after a failed/cancelled SumUp connected attempt and MUST allow another payment attempt without a dead “nothing to settle” state caused by concurrent collection.

## Impact

- **Pi frontend**: `App.vue` terminal busy overlay; `resolvePayment.ts` / `sumupCheckout.ts` abort + terminate; failure sheet component; `useSplitPay` / `PayOrderView` paying lock for whole collection; Register/table/collective/order pay entry points via shared helpers.
- **Pi backend / cloud edge**: likely no new endpoints (terminate + status already exist); possibly small status/error clarity only if needed for distinct failure copy.
- **Customer display**: leave SumUp waiting state on fail/cancel (existing show/hide hooks on register).
- **Tests**: Pi frontend unit/component tests for cancel, failure sheet, and double-submit lock; extend SumUp checkout collection tests.
