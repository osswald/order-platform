## Why

Payment receipt reprints from Belege already mark Bluetooth (Android) slips with «Kopie / Nachdruck», but network/station reprints drop the `reprint` flag, so Pi (and Android Bluetooth fallback) slips look like originals. Staff need a clear reprint marker on every reprint path.

## What Changes

- Thread `reprint` from the Pi PWA Belege reprint flow through `POST /v1/payments/{id}/receipt/print` into the deferred payment-receipt render context.
- When `reprint` is true, network-printed payment receipts SHALL include the same «Kopie / Nachdruck» line already used for Bluetooth ESC/POS.
- First prints after settle remain unmarked (`reprint` false / omitted).
- No change to the printed marker wording (keep «Kopie / Nachdruck»).

## Capabilities

### New Capabilities

- `payment-receipt-reprint`: Reprint marking for payment receipts across Bluetooth ESC/POS and network station print jobs

### Modified Capabilities

- (none)

## Impact

- Pi backend: `PaymentReceiptPrintBody`, `_create_payment_receipt_print_job`, `print_render` payment_receipt branch
- Pi frontend: `printPaymentReceiptToStation` / network branch of `offerPaymentReceipt`
- Tests: payment receipt print-to-station with `reprint: true`; first print without marker
- OpenAPI / generated Pi frontend types if the print body schema is regenerated from Pi OpenAPI
