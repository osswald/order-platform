## Why

Some events use Bluetooth printers on waiter Android devices; others rely only on network ESC/POS printers. Today Bluetooth printing activates whenever a device has a paired printer, with no event-level control in cloud. Operators need a Stammdaten switch (next to the payment-receipt offer toggle) to enable Bluetooth printing per event.

## What Changes

- Add event flag `bluetooth_printing_enabled` (default `false`, opt-in).
- Expose a cloud Stammdaten switch next to «Zahlungsbeleg nach Bezahlung anbieten».
- Include the flag in event CRUD, event copy, and the edge bundle synced to Pi.
- On Pi (Android), use Bluetooth for payment receipts, voucher slips, and shift settlement only when the flag is on; otherwise fall back to network printers.
- Show the waiter hub «Bluetooth Drucker» tile only when the selected event has Bluetooth printing enabled (Admin hub keeps device setup available on Android).

**BREAKING** (behavioral): Waiter Bluetooth print paths that previously ran whenever a printer was paired now require the event flag.

## Capabilities

### New Capabilities

- `event-bluetooth-printing`: Event-level toggle to allow waiter Bluetooth ESC/POS printing, synced via edge bundle and enforced in the Pi PWA.

### Modified Capabilities

- (none)

## Impact

- Cloud backend: `Event` model, schema patches, event schemas/CRUD/helpers, `event_copy`, `EdgeEventBundle`
- Cloud frontend: Stammdaten form, Events.vue wiring, i18n, OpenAPI types
- Pi frontend: payment receipt / voucher / shift print routing; WaiterHubView tile gate
- Tests: cloud backend flag/bundle; Pi frontend unit tests for helpers and hub
