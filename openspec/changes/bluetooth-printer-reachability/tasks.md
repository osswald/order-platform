## 1. Tests first (Pi frontend)

- [ ] 1.1 Extend `androidPrinter` tests for `checkSelectedPrinter` / `isBluetoothPrinterReachable` (ok, error, missing bridge method)
- [ ] 1.2 Extend `paymentReceiptPrompt.test.ts`: configured + reachable → Bluetooth; configured + unreachable → station path + toast; Bluetooth print failure → station fallback when targets exist
- [ ] 1.3 Extend `voucherPrintDestination` tests for unreachable BT → network plan / picker
- [ ] 1.4 Cover shift receipt routing if logic is extracted or gated the same way (unit-testable helper preferred)

## 2. Android bridge

- [ ] 2.1 Extract shared RFCOMM connect helper from `printEscposBase64` in `BluetoothPrinterBridge.kt`
- [ ] 2.2 Implement `checkSelectedPrinter()` with short connect timeout, no ESC/POS payload write, JSON `{ ok, address?|error? }`
- [ ] 2.3 Leave `isAvailable()` / `listPairedPrinters()` / prefs APIs unchanged in meaning

## 3. Pi PWA routing

- [ ] 3.1 Add typed helpers in `androidPrinter.ts` for the probe (and optional thin `isBluetoothPrinterReachable()`)
- [ ] 3.2 Update `offerPaymentReceipt` to prefer Bluetooth only when reachable; on unreachable or print failure, toast and use existing station selection
- [ ] 3.3 Update `resolveWaiterVoucherPrintPlan` with the same reachability gate
- [ ] 3.4 Update shift settlement Bluetooth gate consistently with existing shift network behavior
- [ ] 3.5 Older APK without probe: try Bluetooth when configured; on failure fall through to stations

## 4. Docs and verification

- [ ] 4.1 Update `android/README.md` Bluetooth section (station printers offered when BT unreachable / not selected)
- [ ] 4.2 Run Pi frontend tests and `./scripts/lint.sh` (or staged lint) for touched areas
- [ ] 4.3 Manual Android checklist: printer on → BT receipt; printer off/out of range after settle → toast + station picker/auto; event flag off → stations only; voucher + shift smoke
