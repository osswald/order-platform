## 1. Shared PIN keypad for login

- [x] 1.1 Add/extend tests for `PinKeypad` supporting controlled value (v-model), clear, and no auto-submit when used in controlled mode (admin auto-complete path remains)
- [x] 1.2 Implement controlled `PinKeypad` API (or thin wrapper) suitable for login with explicit parent submit
- [x] 1.3 Add LoginView tests: on-screen keypad digits, Anmelden required, wrong PIN shows error and allows retry
- [x] 1.4 Wire `LoginView` to on-screen PIN keypad + explicit Anmelden; remove `PinNumberInput` from waiter login
- [x] 1.5 Add RegisterSelectView tests mirroring login PIN behaviour (4-digit max, explicit Anmelden)
- [x] 1.6 Wire `RegisterSelectView` to on-screen PIN keypad + explicit Anmelden; remove `PinNumberInput` from register login

## 2. Shift cash amounts

- [x] 2.1 Add tests that shift open/close dialogs expose money keypad entry (no reliance on text input for amount)
- [x] 2.2 Replace `ShiftOpenDialog` amount `<input>` with `MoneyKeypad`, mapping cents ↔ existing shift-open helpers
- [x] 2.3 Replace `ShiftCloseDialog` amount `<input>` with `MoneyKeypad`, mapping cents ↔ existing shift-close helpers

## 3. Custom percent digit entry

- [x] 3.1 Add tests for custom percent path using on-screen digits (order and/or line discount sheets)
- [x] 3.2 Replace custom percent `<input type="number">` in discount sheets with on-screen digit entry (0–100), keeping `MoneyKeypad` for amount mode

## 4. Soft keyboard for non-Android text

- [x] 4.1 Add `SoftKeyboard` (or equivalent) component tests: inserts DE letters including umlauts/`ß`, space, backspace, shift
- [x] 4.2 Implement in-app soft keyboard component styled consistently with existing keypads
- [x] 4.3 Add CollectiveBillNameSheet tests: non-Android uses soft keyboard; Android uses native input (mock `isAndroidApp`)
- [x] 4.4 Wire `CollectiveBillNameSheet` to platform split (in-app keyboard vs native IME)
- [x] 4.5 Add LinePositionSheet comment tests for the same platform split
- [x] 4.6 Wire line-comment entry to platform split; keep note presets working

## 5. Cleanup and verification

- [x] 5.1 Remove unused `PinNumberInput` usages/files if nothing else references them, or leave a brief note if retained intentionally
- [x] 5.2 Run Pi frontend tests (`cd pi/frontend && npm test`) and staged lint (`./scripts/lint.sh --staged`)
