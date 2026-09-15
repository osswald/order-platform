## 1. SumUp collection abort and cancel API wiring

- [x] 1.1 Add an attempt-scoped cancel/abort mechanism to `collectSumupConnectedPayment` in `pi/frontend/src/utils/sumupCheckout.ts` (abort between polls; reject with a dedicated cancelled error; best-effort `terminateSumupCheckout`) and verify with unit tests in `sumupCheckout.test.ts` that cancel during poll terminates and does not return a payment
- [x] 1.2 Ensure timeout and non-cancel failure paths still best-effort terminate and reject without returning a payment; verify existing timeout/failure tests still pass and cover terminate-on-timeout
- [x] 1.3 Export a cancel entry point usable from the App waiting overlay (e.g. module-level cancel for the active attempt) and verify a unit test can cancel an in-flight collection

## 2. Shared waiting overlay cancel + failure sheet

- [x] 2.1 Extend `pi/frontend/src/App.vue` SumUp/`terminalPaymentBusy` overlay with an **Abbrechen** control that invokes the active-attempt cancel; verify component/unit coverage that cancel is rendered while busy and triggers cancel
- [x] 2.2 Add a prominent failure sheet/full-screen message (not toast-only) for SumUp connected decline/fail/timeout, driven from the payment-resolution layer; verify it appears on failure and is absent on operator cancel
- [x] 2.3 Wire dismiss of the failure sheet to return to the prior settle/pay context without auto-starting a new SumUp checkout; verify with a unit/component test
- [x] 2.4 Map cancel to quiet handling (same idea as Twint `'cancelled'`) in `resolvePaymentsForAmount` / settle callers so cancel does not show the failure sheet or an error toast; verify with tests in `resolvePayment.sumup.test.ts` (and split-pay if needed)

## 3. Concurrent pay lock across settle entry points

- [x] 3.1 In `useSplitPay` (`onGreenCheck` / `paying`), hold the busy/paying lock for the entire `paymentsForAmount` + settle window (not only the settle POST) and ignore re-entry while locked; verify with unit tests that a second green-check during an in-flight SumUp collection does not start another collection or settle
- [x] 3.2 Apply the same whole-collection lock on legacy `PayOrderView` (and any other non-split pay path that calls `resolvePaymentsForAmount` for `sumup_connected`); verify with a focused test or shared helper test that re-entry is blocked while `terminalPaymentBusy` is true
- [x] 3.3 Confirm register, table, and collective settle screens all go through the locked split-pay path (no parallel unlocked SumUp start); verify by code inspection plus existing/extended settle tests if present

## 4. Customer display restore (no regression)

- [x] 4.1 Ensure register `onSumupShow` / `onSumupHide` (or equivalent) still restore cart display on both failure and cancel; verify with existing register display/payment tests or a small extension that hide runs after fail and cancel

## 5. Validation

- [x] 5.1 Run Pi frontend unit tests for touched modules (`sumupCheckout`, `resolvePayment`, `useSplitPay`, App overlay/failure sheet) and fix failures until green
- [x] 5.2 Run `openspec validate sumup-payment-fail-cancel-ux --strict` and ensure the change passes
