# Android QA — fullscreen safe layout

Manual checks on a physical Android device (Play Review Demo and, if available, a real venue Pi).

## Audit note (payment-flow sheets)

Full-bleed content (`position: fixed; inset: 0` on the sheet panel) needing `--safe-top`: **TwintQrSheet** (fixed in this change). **QtyInputModal** already pads top+bottom.

Bottom sheets used in payment/order (payment type picker, receipt prompt, pay-table actions, article/additions pickers, discount sheets): only backdrops are full-bleed; panels sit at the bottom with `--safe-bottom` only — no top-inset change required.

## Non-regression (should already look OK)

- [ ] Waiter hub: title clearly below status bar / hole-punch
- [ ] Tisch abrechnen keypad: comfortable top spacing
- [ ] Offene Tische / Sammelrechnungen / Lagerbestand / Bluetooth Drucker: same

## Fullscreen POS (with Belege FAB / emulated printer)

- [ ] **Order** (empty cart): header clear of status bar; cart + article grid share vertical space (no huge empty void with content crammed at top)
- [ ] **Pay table**: header clear of status bar; Rest bar at bottom of safe area; panels expand between header and Rest
- [ ] **TWINT QR**: title/amount below status bar; Fertig/Abbrechen above nav bar and tappable

## Fullscreen POS (real venue Pi, no Belege FAB)

- [ ] Same three checks as above (especially TWINT top inset)

## Wide hosted demo (desktop browser optional)

- [ ] Emulated printer + wide layout: Pi column + receipts side-by-side still works; order/pay not broken
