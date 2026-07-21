## Context

Kitchen order tickets (`KitchenTicketColumn.vue`) show a two-button footer: **Teildruck** and **Komplettdruck**. The footer uses CSS Grid `1fr 1fr` inside a ticket capped near `KITCHEN_MIN_COLUMN_WIDTH_PX` (260px) with `overflow: hidden`. Global `.btn` adds generous horizontal padding.

On iPad Safari (iPadOS 16.7.6), those buttons appear oversized with no visible labels (outline / primary fill only). Header controls on the same screen render correctly. Chrome desktop is fine. Root cause: WebKit `<button>` items resist shrinking below intrinsic nowrap content width (`min-width: auto` + UA nowrap), so `1fr` tracks behave like `minmax(auto, 1fr)`, the pair overflows the ticket, and clipping hides the centered labels.

## Goals / Non-Goals

**Goals:**

- Make both action labels fully readable inside the ticket on Safari/WebKit and Chromium.
- Keep the two-button side-by-side layout when space allows.
- Preserve existing labels, disabled rules, and print emit behavior.
- Prefer a scoped CSS fix over renaming labels or restructuring the kitchen board.

**Non-Goals:**

- Redesigning kitchen multi-column / masonry layout.
- Changing print API or selection logic.
- Global restyle of all `.btn` usages across the Pi app.
- Guaranteeing single-line labels on every width (wrap is acceptable).

## Decisions

### 1. Fix shrink behavior with `minmax(0, 1fr)` + `min-width: 0`

- **Choice:** `.ticket-actions { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }` and `.action-btn { min-width: 0; }`.
- **Why:** Standard cure for Safari grid items that won’t shrink below content size; matches known WebKit/`button` grid blowouts.
- **Alternatives:** Stack buttons vertically always (more height, less kitchen density); shorten labels (“Teil” / “Komplett”) — worse UX and i18n churn for a layout bug.

### 2. Allow label wrap and tighten action-button padding

- **Choice:** `white-space: normal` on `.action-btn`; reduce horizontal padding vs global `.btn` (e.g. `0.35rem–0.5rem`) while keeping `min-height: 44px` for touch.
- **Why:** Long German compounds have no spaces; without wrap, intrinsic width stays large even after minmax(0). Tighter padding recovers horizontal room.
- **Alternatives:** `text-overflow: ellipsis` + nowrap — hides meaning; `hyphens: auto` alone is unreliable for compound German on iOS.

### 3. Reset WebKit button appearance on action buttons only

- **Choice:** `appearance: none; -webkit-appearance: none;` on `.action-btn` (scoped).
- **Why:** Older iOS Safari can paint custom backgrounds while label box sizing stays odd without an appearance reset; header buttons already look fine, so keep the change local.
- **Alternatives:** Global `.btn { appearance: none }` — broader blast radius; skip unless still broken after shrink/wrap.

### 4. Optional hardening: text-size-adjust on kitchen monitor only if still inflated

- **Choice:** Prefer not to add `-webkit-text-size-adjust: 100%` globally in this change. Revisit only if device QA still shows inflated action type after the grid fix.
- **Why:** Text-size-adjust can affect other kitchen chrome; shrink/wrap should be enough for the reported clip.

### 5. Verification via component test + manual iPad check

- **Choice:** Vitest assert both labels render and action-row CSS includes shrink-friendly rules (or snapshot/class checks consistent with existing Pi frontend tests). Manual confirm on iPad Safari 16.
- **Why:** Automated browsers won’t fully reproduce WebKit clipping; unit tests still lock the CSS contract so regressions don’t reintroduce `1fr`/`auto` mins.

## Risks / Trade-offs

- **[Risk] Wrapped two-line labels look slightly taller on narrow tickets** → Mitigation: acceptable; keep font-weight and contrast; avoid stacking unless wrap still overflows after QA.
- **[Risk] `appearance: none` changes default focus/tap chrome** → Mitigation: keep existing border/background/min-height; visual check on Chrome + Safari.
- **[Risk] Fix incomplete if multi-column also clips card bottoms** → Mitigation: symptoms were label-less color blocks with header OK; if footer still clips after grid fix, follow up on `overflow` / column fragmentation separately.

## Migration Plan

- Ship as a normal Pi frontend CSS/component change via PR; no data migration.
- Rollback: revert the scoped style changes.

## Open Questions

- None blocking. Confirm on physical iPad after implement; if wrap still awkward, consider stacking actions below a breakpoint as a follow-up.
