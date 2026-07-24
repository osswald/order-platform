## Context

Waiter Android devices already support Classic Bluetooth ESC/POS via `AndroidPrinterBridge` and the Pi PWA (`androidPrinter.ts`). Pairing is device-local. Cloud already has event Stammdaten flags such as `offer_payment_receipt` that sync through `EdgeEventBundle`. There is no cloud gate for Bluetooth printing today.

## Goals / Non-Goals

**Goals:**
- Event-level opt-in flag for Bluetooth printing, editable in cloud next to the payment-receipt toggle
- Sync the flag to Pi via the existing edge bundle
- Gate Pi Bluetooth print paths (payment receipt, voucher slips, shift settlement) and the waiter hub setup tile

**Non-Goals:**
- Changing Android native pairing / SPP stack
- Storing Bluetooth MAC addresses in cloud
- BLE (Low Energy) support
- Forcing Pi backend to reject `voucher_print_via_bluetooth` (frontend gate is sufficient for this change)

## Decisions

1. **Field name `bluetooth_printing_enabled`, default `false`**  
   Matches other event feature flags (`offer_payment_receipt`, `vouchers_enabled`). Opt-in so events without waiter BT printers stay on network printing. Operators who already use BT must enable the switch after deploy.

2. **Same Stammdaten placement as payment-receipt switch**  
   Both concern receipt delivery on the waiter device; keep them adjacent under payment settings.

3. **Frontend-only enforcement on Pi**  
   Mirror `offer_payment_receipt`: read the flag from the synced event and skip BT when false. Device pairing remains available from Admin hub regardless of event.

4. **Waiter hub tile gated; Admin hub not gated**  
   Waiters only see Bluetooth setup when the selected event allows it. Admins can still pair printers for upcoming BT events.

## Risks / Trade-offs

- [Existing BT events stop using Bluetooth until flag is enabled] → Document in release notes / PR; consider a one-time ops checklist for active events.
- [Stale Pi bundle without the new field] → Treat missing/falsey as disabled (`Boolean(event?.bluetooth_printing_enabled)`).

## Migration Plan

1. Deploy cloud (schema patch adds column default false).
2. Enable the switch on events that use waiter Bluetooth printers.
3. Sync Pis so the flag appears in the bundle.
4. Rollback: removing the UI/flag restores previous “always BT if paired” only if code is reverted; leaving the column is harmless.
