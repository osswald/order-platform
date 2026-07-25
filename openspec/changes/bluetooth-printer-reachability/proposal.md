## Why

After settling an open order, waiters are asked whether to print a payment receipt. Today the Android app treats a **saved Bluetooth printer address** as “ready”: if configured (and the event flag is on), the receipt always goes to Bluetooth and **station printers are never offered**. Bonding / a stored address does not mean the printer is powered on or in range. When the printer is offline, print fails with an error and there is no fallback — which breaks the common case “print on the mobile BT printer if available, otherwise choose a station printer.”

## What Changes

- Add a native Android bridge probe that tries a short RFCOMM connect to the **selected** Bluetooth ESC/POS printer and reports whether it is reachable (without printing a receipt).
- Expose that result to the Pi PWA (`androidPrinter` helpers).
- Change payment-receipt routing so Bluetooth is used only when configured **and** reachable; otherwise keep the existing station/register selection path.
- On Bluetooth print failure after a successful probe (or if probe is unavailable on older APKs), fall through to station selection instead of stopping at an error-only toast.
- Apply the same prefer-BT-if-reachable rule to voucher slip planning and shift settlement receipts for consistency.
- Update Android waiter docs that currently say station printers are only offered when no Bluetooth printer is selected.
- **Not BREAKING** for cloud/Pi receipt APIs or event schema; no new event flags.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `event-bluetooth-printing`: Prefer Bluetooth only when the selected printer is reachable; otherwise fall back to network/station printer selection for payment receipts, vouchers, and shift receipts.

## Impact

- **Android app**: `BluetoothPrinterBridge.kt` (new probe method; shared connect helper with timeout); possibly `android/README.md`.
- **Pi frontend**: `androidPrinter.ts`, `paymentReceiptPrompt.ts`, `voucherPrintDestination.ts`, `useShiftSession.ts`, and related Vitest coverage.
- **Docs**: `android/README.md` Bluetooth receipt section.
- **Cloud / Pi backends**: no API or schema changes expected.
- **Older APKs**: missing probe method must fail open to a safe path (try print or treat as unreachable → stations) without crashing.
