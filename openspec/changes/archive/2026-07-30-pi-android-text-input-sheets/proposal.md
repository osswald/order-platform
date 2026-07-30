## Why

On Android, creating a Sammelrechnung from Offene Posten opens a bottom sheet whose Name field is covered by the soft keyboard, and creating one from the Sammelrechnungen list uses `window.prompt`, which surfaces a WebView JS dialog with the page URL. The same `window.prompt` pattern appears when closing a shift (cash count). Waiters need in-app naming/amount UI that stays usable with the keyboard up.

## What Changes

- Replace all Pi frontend `window.prompt` call sites with in-app dialogs/sheets (Sammelrechnung create from the list; shift cash-count on end-shift).
- Use the **same** name-entry UX for Sammelrechnung create from the hub list as already used when assigning open positions (`PayTableActionsSheet` → «Neue Sammelrechnung» with Name field + primary action).
- Keep soft-keyboard avoidance scoped to **sheets that contain text inputs** (lift/pad those sheets so the focused field and primary action stay visible). Sheets without text inputs are unchanged.
- Do not introduce a global IME → `--safe-bottom` remap for all bottom chrome.

## Capabilities

### New Capabilities

- `pi-android-text-input-sheets`: In-app text entry for Sammelrechnung naming and shift cash-count (no `window.prompt`), shared Sammelrechnung create UX, and keyboard-aware layout only for sheets that contain text inputs.

### Modified Capabilities

- `register-order-settlement`: Create-from-list Sammelrechnung UX must match assign-flow naming (no native prompt).
- `pi-android-safe-layout`: Extend with keyboard avoidance for text-input sheets only (system-bar inset rules unchanged for non-input sheets).

## Impact

- Pi frontend: `OpenCollectiveBillsView.vue`, `PayTableActionsSheet.vue` (shared name step / extract), `useShiftSession.ts` + shift close dialog (alongside existing `ShiftOpenDialog`), text-input sheets (`LinePositionSheet`, `LineDiscountSheet`, `OrderDiscountSheet`, and the Sammelrechnung name sheet), optional small composable for keyboard inset padding.
- Android app: optional — prefer WebView/`visualViewport`-based sheet lift so non-input sheets stay untouched; no backend/API changes.
- Tests: Vitest updates for prompt removal and shared create UX; CSS/composable coverage for keyboard padding where practical.
