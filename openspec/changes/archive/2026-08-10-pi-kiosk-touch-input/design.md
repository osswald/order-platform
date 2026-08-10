## Context

See proposal.md for motivation. Pi frontend already has touch-first digit entry for tables (`TableKeypad`), money (`MoneyKeypad`), and admin PIN (`PinKeypad`), but waiter/register login and several daily dialogs still use native `<input>` fields. Android detection already exists via `isAndroidApp()`; text sheets already lift for the native IME via `useKeyboardBottomInset`.

## Goals / Non-Goals

**Goals:**

- One input model for daily waiter/register flows on all appliances (no device-type feature flag beyond Android vs not).
- Reuse existing keypad components where they fit; extend rather than fork.
- Platform split only for free-text: in-app soft keyboard off Android; native IME on Android.

**Non-Goals:**

- Setup/pairing/connection URL / unpair secret / admin load-test forms.
- Detecting “Elo” or a generic “kiosk mode” flag.
- Changing PIN validation rules, auth APIs, or backend PIN length limits.
- Replacing checkbox/radio/tap pickers (already touch-native).

## Decisions

### 1. Always on-screen for PIN / money / digits (all clients)

**Choice:** Waiter login, register login, shift cash amounts, and custom percent use on-screen keypads on every client, including Android.

**Why:** Matches existing POS patterns (`MoneyKeypad`, `TableKeypad`, `PinKeypad`). Avoids depending on IME for the critical path. Android tablets still benefit from large touch targets.

**Alternatives:** Android-only native inputs for money — rejected; inconsistent UX and fails if IME is disabled on an Android kiosk.

### 2. Explicit Anmelden for PIN (no auto-complete submit)

**Choice:** Extend or adapt `PinKeypad` so the parent owns the current PIN string (v-model or equivalent). Login screens keep **Anmelden** as the only submit. Wrong PIN clears the keypad; reaching a max length does not auto-login.

**Why:** Waiter PINs are variable length (UI max 12); auto-submit at a fixed length is wrong. Product decision: explicit confirm.

**Alternatives:** Assume 4-digit PINs and auto-submit like admin — rejected by product.

**Admin unlock:** Unchanged (still auto-complete on fixed 6-digit admin PIN).

### 3. Shift amounts use MoneyKeypad

**Choice:** Replace the CHF text fields in `ShiftOpenDialog` / `ShiftCloseDialog` with `MoneyKeypad` (cents model), mapping to the existing shift session confirm helpers.

**Why:** Component already implements POS money entry; removes IME dependency for shift start/end.

**Alternatives:** Separate decimal keypad with `.` key — unnecessary; cents-shift entry is already the house pattern.

### 4. Custom percent via digit keypad

**Choice:** When “Andere” percent is selected in discount sheets, enter 0–100 with an on-screen digit keypad (or a thin wrapper), not `<input type="number">`. Amount mode already uses `MoneyKeypad`.

**Why:** Closes the remaining IME hole on the discount path.

### 5. Text: SoftKeyboard on non-Android; native IME on Android

**Choice:** Introduce a shared in-app soft keyboard (DE-friendly: letters + `äöüÄÖÜß`, space, backspace, optional shift) used by `CollectiveBillNameSheet` and line-comment entry when `!isAndroidApp()`. On Android, keep a normal focused `<input>` / textarea and existing `useKeyboardBottomInset` lift.

**Why:** Product decision. Android already has a working IME + inset bridge; Elo/kiosk browsers without IME need the in-app keyboard.

**Alternatives:** Always in-app keyboard — rejected (worse Android UX, fights the IME). Always native — fails on non-Android kiosks.

### 6. Soft keyboard layout scope

**Choice:** Single QWERTY-like DE layout sufficient for names/comments (no number row required if digits are rare; include digits if cheap). No emoji, no autocomplete, no dictation.

**Why:** Comments and Sammelrechnung names are short German/Swiss German strings; keep the component small.

### 7. Deprecate PinNumberInput on login paths

**Choice:** Stop using `PinNumberInput` on waiter/register login. Leave the component in the tree only if still referenced elsewhere; otherwise remove or keep unused until a follow-up cleanup.

**Why:** Login must not depend on system keyboard.

## Risks / Trade-offs

- **[Risk] Soft keyboard eats vertical space on small viewports** → Mitigation: dock keyboard below the field inside the sheet; keep field + primary action visible; allow scrolling the sheet body above the keyboard.
- **[Risk] `isAndroidApp()` false in mobile Chrome** → Mitigation: acceptable — in-app keyboard still works; native IME may also appear if a focusable field remains — prefer readonly/display field + SoftKeyboard-driven updates on non-Android so the system IME does not open.
- **[Risk] Variable-length PIN + empty Anmelden** → Mitigation: disable or no-op Anmelden when PIN empty; show existing error strings on mismatch.
- **[Trade-off] Two text-entry code paths** → Shared sheet shell with a small `useNativeTextInput = isAndroidApp()` branch keeps duplication low.

## Migration Plan

- Ship as a normal Pi frontend change; no data migration.
- Rollback: revert the frontend deploy / app WebView asset; no server coupling.
- No feature flag required for v1 (behaviour is additive UX replacement).

## Open Questions

None that block specs or tasks. Soft-keyboard visual styling can follow existing keypad CSS variables during implementation.
