## 1. Tests first (Pi frontend)

- [x] 1.1 Extend `androidPrinter` tests for `checkSelectedPrinter` / `isBluetoothPrinterReachable` (ok, error, missing bridge method)
- [x] 1.2 Extend `paymentReceiptPrompt.test.ts`: configured + reachable → Bluetooth; configured + unreachable → station path + toast; Bluetooth print failure → station fallback when targets exist; handled print failures do not reject
- [x] 1.3 Extend `voucherPrintDestination` tests for unreachable BT → network plan / picker
- [x] 1.4 Cover shift receipt routing if logic is extracted or gated the same way (unit-testable helper preferred)
- [x] 1.5 Add/extend settle-screen (or extracted `onPay` helper) tests: successful settle + failing `offerPaymentReceipt` still emits `settled` / continues; same for `PayOrderView` navigation after pay

## 2. Android bridge

- [x] 2.1 Extract shared RFCOMM connect helper from `printEscposBase64` in `BluetoothPrinterBridge.kt`
- [x] 2.2 Implement `checkSelectedPrinter()` with short connect timeout, no ESC/POS payload write, JSON `{ ok, address?|error? }`
- [x] 2.3 Leave `isAvailable()` / `listPairedPrinters()` / prefs APIs unchanged in meaning

## 3. Pi PWA routing

- [x] 3.1 Add typed helpers in `androidPrinter.ts` for the probe (and optional thin `isBluetoothPrinterReachable()`)
- [x] 3.2 Update `offerPaymentReceipt` to prefer Bluetooth only when reachable; on unreachable or print failure, toast and use existing station selection; do not reject after handled print errors
- [x] 3.3 Update `resolveWaiterVoucherPrintPlan` with the same reachability gate
- [x] 3.4 Update shift settlement Bluetooth gate consistently with existing shift network behavior
- [x] 3.5 Older APK without probe: try Bluetooth when configured; on failure fall through to stations

## 4. Settle completion isolation

- [x] 4.1 In `SplitPaySettleScreen.onPay`, isolate receipt errors so full settle always `emit('settled')` (and partial settle still refreshes) after successful payment
- [x] 4.2 In `PayOrderView.pay`, isolate receipt errors so hub navigation always runs after successful pay
- [x] 4.3 Audit other `offerPaymentReceipt` callers (e.g. reprint) so intentional error surfacing remains correct

## 5. Docs and verification

- [x] 5.1 Update `android/README.md` Bluetooth section (station printers offered when BT unreachable / not selected; settle continues if print fails)
- [x] 5.2 Run Pi frontend tests and `./scripts/lint.sh` (or staged lint) for touched areas
- [ ] 5.3 Manual Android checklist: printer on → BT receipt + leave screen when fully settled; printer off/out of range after settle → toast + station path + leave screen (not stuck on split-pay); event flag off → stations only; voucher + shift smoke (see `qa-android.md`)
