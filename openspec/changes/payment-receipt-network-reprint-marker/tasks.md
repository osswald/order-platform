## 1. Backend tests

- [x] 1.1 Add failing test: `POST /v1/payments/{id}/receipt/print` with `reprint: true` yields a print job whose rendered ESC/POS contains «Kopie / Nachdruck»
- [x] 1.2 Add/adjust test: same print without `reprint` (or `false`) does not contain «Kopie / Nachdruck»

## 2. Backend implementation

- [x] 2.1 Add `reprint: bool = False` to `PaymentReceiptPrintBody`
- [x] 2.2 Pass `reprint` into payment-receipt render context from `_create_payment_receipt_print_job` / print route
- [x] 2.3 Honor `reprint` in `build_escpos_from_render_context` when calling `build_payment_receipt_text`
- [x] 2.4 Run Pi backend payment-receipt tests and confirm they pass

## 3. Frontend tests and wiring

- [x] 3.1 Add failing frontend test: network branch of `offerPaymentReceipt` with `reprint: true` posts `{ station_uuid, reprint: true }`
- [x] 3.2 Thread `reprint` through `printPaymentReceiptToStation` / `printToStation` / `printViaNetworkTargets`
- [x] 3.3 Run Pi frontend related Vitest tests and confirm they pass

## 4. Verify

- [x] 4.1 Run affected Pi backend + frontend test suites
- [x] 4.2 Run `./scripts/lint.sh --staged` (or full lint) before commit
