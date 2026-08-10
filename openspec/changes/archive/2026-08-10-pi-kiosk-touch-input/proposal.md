## Why

Kiosk touchscreens (e.g. Elo) often have no physical keyboard and no reliable system IME. Waiter and cash-register login currently use a native `<input>` PIN field, so operators cannot sign in. The same gap blocks other daily POS flows that still depend on system text/number entry (shift cash counts, custom percent discounts, Sammelrechnung names, free-text line comments).

## What Changes

- Replace waiter and cash-register PIN fields with an on-screen digit keypad; login submits only via explicit **Anmelden** (no auto-submit when a length is reached).
- Use on-screen money/digit keypads for shift open/close cash amounts and for custom percent discount entry (all appliances).
- For short operational text (Sammelrechnung name, line comments): provide an in-app full soft keyboard on non-Android clients; on Android keep the native IME (existing keyboard-inset behaviour).
- Apply these patterns on all appliances (no Elo/kiosk detection flag).
- **Out of scope:** pairing code, unpair secret, connection/sync URL, and other rare setup/admin text fields.

## Capabilities

### New Capabilities

- `pi-kiosk-touch-input`: Touch-first operator input for Pi waiter/register daily flows — on-screen PIN/money/digit entry everywhere, and platform-specific text entry (in-app soft keyboard vs Android native IME).

### Modified Capabilities

- (none)

## Impact

- **Pi frontend:** `LoginView`, `RegisterSelectView`, `ShiftOpenDialog`, `ShiftCloseDialog`, discount sheets (custom %), `CollectiveBillNameSheet`, `LinePositionSheet` comment field; reuse/extend `PinKeypad` / `MoneyKeypad`; new soft-keyboard component for non-Android text.
- **Android app:** no required native changes for text (native IME remains); digit/PIN keypads are web UI.
- **APIs / backend:** none.
- **Tests:** component and view tests for keypad login, shift amounts, and text-entry platform split.
