## Context

Payment receipts after settlement are orchestrated by `offerPaymentReceipt` (`pi/frontend/src/utils/paymentReceiptPrompt.ts`):

1. Ask whether to print.
2. If Android + selected BT address + `event.bluetooth_printing_enabled` → Bluetooth ESC/POS via `printPaymentReceipt` / `AndroidPrinter.printEscposBase64`.
3. Else → `receiptPrintTargets` (stations / registers with `printer_hosts`) → preferred / single / picker.

`isBluetoothPrinterConfigured()` only checks SharedPreferences for a non-empty address. Native `listPairedPrinters()` returns OS **bonded** devices; bonding ≠ in range. Each print opens a Classic BT SPP (RFCOMM) socket, writes, and closes — there is no persistent session or existing ping API.

The same “configured ⇒ Bluetooth” gate exists for waiter vouchers (`resolveWaiterVoucherPrintPlan`) and shift close receipts (`printShiftReceipt`). Android README currently documents that station printers are only offered when no Bluetooth printer is selected.

### Settle UI stuck after BT print failure

`SplitPaySettleScreen.onPay` awaits settlement (`onGreenCheck`), then `await offerPaymentReceipt(...)`, then only if fully settled emits `settled` (parents navigate via `goHub` / `goBack`). `printBluetooth` toasts and **rethrows**; that exception is caught by `onPay`’s outer `catch`, so **`emit('settled')` never runs** even though the payment already succeeded. Result: order/account is settled in the backend, but the waiter remains on the split-pay screen with stale UI. `PayOrderView.pay` has the same pattern (`router.replace` hub only after the receipt await).

## Goals / Non-Goals

**Goals:**

- Detect whether the **selected** Bluetooth printer answers a short connect before committing to BT for payment receipts.
- If unreachable (or BT print fails), offer the existing station/register path instead of dead-ending on an error toast.
- Keep Bluetooth preference when the printer is actually available (no extra picker friction).
- Align voucher and shift print routing with the same reachability rule.
- Ensure receipt print failures **never** prevent post-settle navigation / `settled` emission / partial-settle continue.
- Cover routing and settle-completion isolation with Vitest; document a short Android manual check.

**Non-Goals:**

- Persistent Bluetooth connections or background keepalives.
- Checking station/network printer health before print.
- iOS / Web Bluetooth printers.
- New cloud event flags or receipt API changes.
- Automatically clearing a saved printer address when unreachable.
- Guaranteeing probe success implies a later print will succeed (race: printer can go away between probe and print).
- Undoing or retrying the payment when printing fails.

## Decisions

### 1. Probe via short RFCOMM connect (same path as print)

**Choice:** Add `@JavascriptInterface fun checkSelectedPrinter(): String` on `BluetoothPrinterBridge` that:

1. Validates permission, adapter, and selected address (same guards as print).
2. `createRfcommSocketToServiceRecord(SPP UUID)` → `connect()` with a short timeout → close without writing payload (or write nothing).
3. Returns JSON `{ "ok": true, "address": "…" }` or `{ "ok": false, "error": "…" }`.

Extract shared connect logic from `printEscposBase64` so probe and print stay consistent.

**Alternatives considered:**

- Bonded list / `bondState` only — false positives when printer is off.
- Try-print-then-fallback only — simpler, but slower and may leave a partial failed attempt; probe-first is clearer UX.
- BLE GATT / Web Bluetooth — not used by this ESC/POS Classic stack.

### 2. Connect timeout ~2–3 seconds

**Choice:** Bound the probe so settle UX stays snappy (target ≤ ~3s worst case). On timeout, treat as unreachable.

**Alternatives considered:**

- Default blocking `socket.connect()` with no timeout — can hang too long on the WebView bridge thread.
- Very long timeout — feels like a freeze after “Ja” on the receipt prompt.

Implementation note: if a hard socket timeout needs a helper thread, keep the JS-facing API synchronous (string JSON return) like existing printer methods, matching `printEscposBase64`.

### 3. Routing: configured ∧ reachable → BT; else stations

**Choice:** In `offerPaymentReceipt` (and voucher / shift peers):

```text
btConfigured = Android && address saved && event.bluetooth_printing_enabled
if btConfigured && checkSelectedPrinter().ok:
  try printBluetooth
  on failure → toast + fall through to station path (if any targets)
else:
  existing station path
```

When BT was preferred but unreachable, show a short German toast (e.g. «Bluetooth-Drucker nicht erreichbar.») then continue with preferred / single / picker as today.

**Alternatives considered:**

- Always ask “Bluetooth or station?” — extra tap when BT works.
- Probe fail → abort without stations — does not meet the product case.
- Keep voucher/shift on configure-only gate — inconsistent waiter experience.

### 4. Older APK without `checkSelectedPrinter`

**Choice:** If the bridge method is missing, **do not** treat the printer as reachable. Fall through to: attempt Bluetooth print when configured (today’s behavior) **or** treat as unknown and try print then catch → stations.

Preferred concrete rule for missing method: **try Bluetooth print once; on failure fall through to stations** (preserves today’s success path on old APKs; adds fallback). When method exists: **probe first**, then print only if ok.

**Alternatives considered:**

- Fail closed (always stations on old APK) — regresses working BT setups until Play update.
- Fail open as “reachable” without probe — keeps today’s broken offline case.

### 5. No caching across payments

**Choice:** Probe per print decision (or at most within a single `offerPaymentReceipt` call). Do not cache “reachable” for the waiter session — printers move in and out of range during service.

**Alternatives considered:**

- Session cache with TTL — fewer connects, stale “online” risk; not worth it for occasional receipts.

### 6. Receipt failures must not block settle completion

**Choice:** Two complementary fixes:

1. **Callers isolate receipt errors** — In `SplitPaySettleScreen.onPay` and `PayOrderView.pay`, wrap `offerPaymentReceipt` in its own try/catch (or `void`/`finally` pattern) so settle toast + `emit('settled')` / `router.replace` always run after a successful payment, regardless of receipt outcome.
2. **`offerPaymentReceipt` does not reject for handled print failures** — Toast and fall back to stations (or return after toast if no targets); only user cancel of the ask/picker may soft-return without throwing. Prefer not rethrowing from `printBluetooth`/`printToStation` when the error was already surfaced, so other callers cannot accidentally strand navigation.

Settlement remains authoritative: a failed receipt never implies a failed payment.

**Alternatives considered:**

- Only isolate in `SplitPaySettleScreen` — leaves `PayOrderView` / reprint callers inconsistent.
- Only stop rethrowing inside `offerPaymentReceipt` — still fragile if a future caller awaits and a new throw path appears; caller isolation is the hard guarantee for settle UX.
- Reload split-pay summary on receipt error without emitting settled — still wrong when `remaining_cents <= 0` (nothing left to show; should leave the screen).

## Risks / Trade-offs

- **Bridge thread blocking:** Probe/connect runs on the WebView JS bridge thread (same as print today). Mitigate with a short timeout and busy indicator already used during print (`receiptPromptBusy`).
- **False negatives:** Flaky BT or slow printers may fail the probe and push waiters to stations more often — acceptable vs silent BT failure.
- **Probe/print race:** Printer can disappear between probe and print → catch print error and fall through to stations.
- **Double connect cost:** Probe + print = two RFCOMM handshakes when BT works. Acceptable for receipt frequency; avoid writing real payload during probe.
- **Voucher planning:** `resolveWaiterVoucherPrintPlan` runs before order submit; a failed probe may open the station picker earlier in the flow — intentional for parity.
- **Partial settle + receipt fail:** After isolating receipt errors, partial settle must still refresh the split UI (existing `onGreenCheck`/reload behavior) and remain on the screen; only full settle navigates away.

## Migration Plan

1. Ship Android APK with `checkSelectedPrinter` + PWA that probes when present and falls back on print failure.
2. Fix settle/receipt error isolation in the same change so offline BT cannot strand the split-pay / pay-order UI.
3. No data migration; selected address prefs unchanged.
4. Update `android/README.md` wording for station fallback.
5. Manual QA: printer on → BT print; printer off / out of range → toast + station path + leave screen when fully settled; event flag off → stations only; old APK without probe → BT try then station fallback on error.

## Open Questions

- Exact German copy for the unreachable toast (product/i18n polish).
- Whether shift receipts should open the station picker UI or only auto-print to a single/preferred network target when BT is down (today shift network path may differ from payment receipts — match existing shift network behavior, only change the BT gate).
