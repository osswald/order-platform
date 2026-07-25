# Manual Android QA — Bluetooth printer reachability

## Prerequisites

- Android waiter APK with `checkSelectedPrinter`
- Event with `bluetooth_printing_enabled` and `offer_payment_receipt`
- At least one station/register with `printer_hosts`
- Paired ESC/POS printer selected under **Bluetooth Drucker**

## Checklist

- [ ] Printer **on / in range**: settle open order → confirm receipt → prints on Bluetooth; fully settled leaves split-pay screen
- [ ] Printer **off / out of range**: settle → confirm receipt → toast «Bluetooth-Drucker nicht erreichbar.» (or print error) → station picker or auto station print → fully settled leaves split-pay (not stuck)
- [ ] Event flag **off**: configured BT ignored; station path used
- [ ] **Voucher** sale on Android: unreachable BT → network plan / picker
- [ ] **Shift close**: unreachable / failed BT falls back to network shift print
- [ ] Older APK without probe (if available): try BT then station fallback on failure
