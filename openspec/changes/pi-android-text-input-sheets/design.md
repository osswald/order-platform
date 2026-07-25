## Context

The Android waiter app hosts the Pi Vue PWA in a WebView. Two create-Sammelrechnung entry points diverge today:

1. **Assign from Offene Posten / register pay** — `PayTableActionsSheet` step `new-name`: in-app bottom sheet with Name + «Erstellen und zuordnen». Usable UX except the soft keyboard covers the field because the sheet is `position: fixed; bottom: 0` and Android only forwards system-bar insets (not IME) into `--safe-*`.
2. **Hub list «Neue Sammelrechnung»** — `OpenCollectiveBillsView` calls `window.prompt`, which Android paints as a system JS dialog showing the WebView origin URL.

Shift end also uses `window.prompt` for cash count (`maybeEndShiftOnSwitch`), while shift open already uses an in-app centered dialog (`ShiftOpenDialog`).

Decided scope: replace all Pi `window.prompt` usages; unify Sammelrechnung naming UX; lift only sheets that contain text inputs.

## Goals / Non-Goals

**Goals:**

- One Sammelrechnung name-entry UI shared by hub create and assign-create.
- No `window.prompt` left in the Pi frontend.
- Soft keyboard does not obscure Name/amount fields or primary actions on text-input sheets.
- Keyboard avoidance is opt-in per sheet (or via a shared helper used only by those sheets).

**Non-Goals:**

- Global IME remapping of `--safe-bottom` for every bottom bar / non-input sheet.
- Replacing `window.confirm` / `window.alert` everywhere (only as needed inside the shift-close flow that already mixes them with prompt, if that keeps the flow coherent).
- Cloud admin UI or native Android Material dialogs for these flows.
- Changing collective-bill API contracts.

## Decisions

### 1. Shared Sammelrechnung name sheet (same UX as assign)

Extract the existing `new-name` step UI (label «Name», text input, placeholder «z. B. Personal», primary CTA) into a reusable bottom sheet component (e.g. `CollectiveBillNameSheet`), used by:

- `PayTableActionsSheet` (CTA remains «Erstellen und zuordnen»; on confirm → assign with `new_name`)
- `OpenCollectiveBillsView` (CTA «Erstellen» or equivalent; on confirm → `POST /v1/collective-bills` then navigate to settle as today)

**Alternatives considered:** Centered modal like `ShiftOpenDialog` — rejected for Sammelrechnung so both entry points stay visually identical to the assign flow the user already knows.

### 2. Keyboard avoidance via `visualViewport` padding on opt-in sheets

Add a small composable (e.g. `useKeyboardBottomInset`) that listens to `visualViewport` resize/scroll and exposes a pixel inset for the covered bottom region. Text input sheets apply it as extra `padding-bottom` (or `bottom` offset) **in addition to** `--safe-bottom`.

Apply to:

- `CollectiveBillNameSheet` / `PayTableActionsSheet` name step
- `LinePositionSheet`, `LineDiscountSheet`, `OrderDiscountSheet`
- Shift amount dialogs if they remain bottom-anchored; if shift close stays a centered card like open, apply only enough lift/scroll so the field stays above the keyboard (same helper, different layout)

**Alternatives considered:**

- Forward `WindowInsetsCompat.Type.ime()` into `--safe-bottom` globally — rejected (would move Rest bars, FABs, non-input sheets).
- `android:windowSoftInputMode=adjustResize` alone — unreliable with edge-to-edge WebView; still prefer sheet-local padding.

### 3. Shift cash-count: in-app dialog mirroring shift open

Replace `window.prompt` in `maybeEndShiftOnSwitch` with an in-app dialog patterned on `ShiftOpenDialog` (amount field, Abbrechen / confirm). Prefer promise-based pending state in `useShiftSession` (same pattern as `promptShiftOpen`). Keep confirm/cancel semantics; avoid leaving a lone native prompt in that flow.

**Alternatives considered:** Reuse Sammelrechnung bottom sheet — wrong metaphor for cash count; stick to amount dialog family.

### 4. No Android native code required for v1

Prefer pure frontend `visualViewport` handling so Pi browser / PWA and Android stay aligned. Revisit native IME bridge only if device QA shows `visualViewport` insufficient on target WebViews.

## Risks / Trade-offs

- [visualViewport quirks on older System WebViews] → Gate helper to no-op when API missing; verify on Play Review Demo device; fall back to `window.innerHeight` delta if needed.
- [Shared sheet extraction regresses assign flow] → Keep existing tests; add hub-create tests that assert no `window.prompt` and sheet presence.
- [Shift close confirm still native] → Optionally fold confirm into the same dialog sequence so the end-shift path is fully in-app; do not expand a repo-wide confirm purge.

## Migration Plan

1. Land frontend change via PR (Pi frontend + tests); no schema/migration.
2. Ship with next Android bundled frontend / OTA as usual.
3. Rollback: revert PR; no data migration.

## Open Questions

- None — product decisions locked: fix all prompts, same Sammelrechnung UX, keyboard lift only on text-input sheets.
