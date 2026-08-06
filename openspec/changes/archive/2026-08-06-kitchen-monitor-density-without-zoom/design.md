## Context

PR #258 added `.kitchen-monitor { zoom: 0.8; width/height: calc(100% / 0.8) }` so Bestellungen could fit ~four columns. Layout used a 125% containing block; Produkte (`flex-wrap`) and the header (`space-between`) broke: wrap/clip against the fake-wide box, and right-side controls sit off-screen. Browser page zoom made Produkte worse.

Target: keep denser Bestellungen on tablet landscape without CSS zoom.

## Goals / Non-Goals

**Goals:**

- Remove CSS zoom and compensating size from the kitchen monitor root.
- Fit ≥4 ticket columns on ~1024 CSS px tablet landscape via lower min column width (+ existing 6px gap).
- Produkte cards wrap within the visible viewport; kitchen header controls stay fully visible.
- Optional mild font-size scale on the kitchen route only if tickets still feel oversized after the width change (must not widen the containing block).

**Non-Goals:**

- Reintroducing CSS `zoom` / `transform: scale` with width compensation.
- Configurable zoom UI.
- Changing pickup / customer-display density.

## Decisions

### 1. Drop zoom; densify with min column width

- **Choice**: Delete `--kitchen-zoom` / `zoom` / compensating width & height. Set `KITCHEN_MIN_COLUMN_WIDTH_PX` ≈ 190–200 so `computeKitchenColumnLayout(1024)` yields ≥4 columns with `KITCHEN_ORDER_GAP_PX = 6`.
- **Why**: Column count tracks true `clientWidth`; flex wrap and header flex use the same width.
- **Alternative**: Zoom only `.kitchen-body` for orders — rejected (mixed density, still fiddly with ResizeObserver).

### 2. Optional kitchen `font-size` scale (not rem-root of the app)

- **Choice**: If visual density still feels large after ~190px columns, set e.g. `font-size: 0.9em` (or `%`) on `.kitchen-monitor` so rem-less/`em`/`%` ticket chrome shrinks slightly. Prefer not changing global `html` font-size.
- **Why**: Approximates “80% look” without changing containing-block width. Ticket styles mostly use `rem` today — if rem-based, either convert critical sizes to `em` under the scaled root or accept width-only density. Prefer width-first; only add font scale if QA still wants smaller type.
- **Default for apply**: Start with width-only; add `font-size: 90%` on `.kitchen-monitor` if rem children won’t shrink (then ticket rem won’t change — so font scale alone is weak). Practical path: width + slightly tighter ticket padding/title sizes only if needed. **Apply default: width + gap only; no zoom; skip global font-size unless a follow-up is needed.**

### 3. Spec rewrite for `kitchen-monitor-layout`

- Replace zoom scenarios with: no CSS zoom; ≥4 columns at 1024px true width; products wrap; header fully visible.

## Risks / Trade-offs

- **[Risk] Tickets feel larger than 80% browser zoom** → Mitigation: tune min width (190 vs 200); optional later typography pass.
- **[Risk] Very narrow phones get many thin columns** → Mitigation: keep a sane min (≥180); single-column still works under min.
- **[Trade-off]** Not pixel-identical to browser 80% zoom — accepted for layout correctness.

## Migration Plan

1. Land on a branch from current main (or follow-up on denser-columns if still open).
2. Remove zoom CSS; lower min width; update tests/contracts.
3. Manual QA: Bestellungen 4 columns; Produkte wrap under Chrome zoom; header controls visible on Android immersive + desktop.

## Open Questions

- None blocking; exact min width (190 vs 200) chosen in apply from the ≥4@1024 test.
