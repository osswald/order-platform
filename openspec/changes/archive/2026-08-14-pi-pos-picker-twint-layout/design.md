## Context

See proposal.md — Why.

**Position wählen** (`LayoutCellPickerSheet`) and **Zusätze** (`AdditionsPickerSheet`) already share `.sheet.sheet--picker` and `.sheet-option-row`. Zusätze rows are `<label>`s (inherit body type). Position wählen rows are `<button class="sheet-option-row__control--btn">` via `SheetOptionList`; user-agent button styles typically do not inherit `font-size`. Position wählen’s footer sets `min-height: 48px`; Zusätze actions use shared `.btn` (`min-height: 44px`, `font-size: 1rem`).

**TWINT operator sheet** (`TwintQrSheet`) is `position: fixed; inset: 0` with a column flex layout (QR `flex: 1`, actions at the end) but also has class `sheet`, which sets `max-height: 70vh`. The 70vh cap wins, so the sheet hangs from the top and actions sit mid-viewport. The QR itself was further capped at `min(92vw, 360px)` / `min(60vh, 360px)`, so after fullscreen it still sat small in the middle. Android is the same Vue sheet in a WebView. `html.android-app` already pads `--safe-top` / `--safe-bottom` on the sheet.

**Customer display** (`RegisterDisplayView` `.twint-panel`) draws a rounded grey border. The QR used `max-height: calc(100dvh - 2rem)` with `align-items: center`, so the white QR card overflowed and painted over the border.

`SheetOptionList` is also used by `VoucherRedeemSheet` (not a POS order picker). Style the layout-cell picker without changing voucher redeem unless the shared button-inherit rule is applied globally with no visual harm.

## Goals / Non-Goals

**Goals:**

- Align Position wählen type and control metrics with Zusätze via shared CSS, not a one-off copy of Zusätze markup
- Override the inherited `.sheet` max-height on the TWINT sheet so `inset: 0` + column flex actually fill the viewport
- Scale the operator TWINT QR to the remaining flex region with padding on all sides (`object-fit: contain`)
- Clip/constrain the customer-display TWINT QR so it stays inside the rounded panel
- Keep Android safe-area padding and hosted-demo **width** constraint (`body.hosted-pi-demo--wide .sheet`)

**Non-Goals:**

- Stretching `EventLayoutGrid` cells
- Making Position wählen a fullscreen takeover
- Changing ArticlePickerSheet unless it falls out of the shared `.sheet--picker` option-button rule
- Native Android TWINT UI (none exists)
- Payment confirm/cancel semantics

## Decisions

1. **Fix option type by inheriting font on picker option buttons**  
   Under `.sheet--picker`, set `font: inherit` (or `font-size`/`font-family` inherit) on `.sheet-option-row__control--btn` so Position wählen matches Zusätze labels.  
   **Alternatives considered:** Convert option rows to `<label>`/`<div>` — larger markup change, worse semantics for a tap-to-pick list. Restyle only inside `LayoutCellPickerSheet.vue` scoped CSS — duplicates the shared row contract.

2. **Match option and footer control height to Zusätze / `.btn`**  
   Give picker option buttons the same padding and min-height as Zusätze rows (shared `.sheet-option-row__control` padding; add a min-height if buttons still collapse). Drop LayoutCellPickerSheet’s extra `min-height: 48px` on footer **Abbrechen** so it uses `.btn` like Zusätze.  
   **Alternatives considered:** Enlarge Zusätze to match Position wählen — operator asked for the reverse. Give Position wählen a min-height sheet — rejected; it stays a content-sized bottom sheet.

3. **TWINT: override `max-height` (and `overflow`) on `.twint-qr-sheet`**  
   Keep `inset: 0` + column flex. Set `max-height: none` (and `height: 100%` or equivalent) and `overflow: hidden` so global `.sheet { max-height: 70vh; overflow: auto }` cannot shrink it. Existing QR `flex: 1` then pushes **Fertig** / **Abbrechen** to the bottom.  
   **Alternatives considered:** Remove class `sheet` from TWINT — more CSS duplication. Change global `.sheet` max-height — would enlarge every bottom sheet.

4. **Operator QR fills `.qr-wrap` with all-sides padding**  
   Drop the 360px / 60vh cap. Set `.qr-wrap { padding: 1rem }` and `.qr-image { width/height: 100%; object-fit: contain }` so the image scales to the leftover column without touching header, actions, or sheet edges.  
   **Alternatives considered:** A larger fixed cap (e.g. 480px) — still leaves empty space on tall phones. `width: auto` without 100% height — does not grow to fill.

5. **Customer-display QR: stretch panel + `max-height: 100%` + `overflow: hidden`**  
   In `RegisterDisplayView`, stop using `max-height: calc(100dvh - 2rem)`. Stretch `.twint-panel` children, size the image to the QR column (`max-height: 100%`), and clip overflow to the rounded border.  
   **Alternatives considered:** Only `overflow: hidden` — would hide bleed but still press the card flush against the inner edge. Padding-only without clipping — can still overflow on large QR assets.

6. **Contract tests, not screenshot tests**  
   Extend the existing CSS/source contract style (`androidSafeLayout.contract.test.ts`, `posOrderSheets.contract.test.ts`, `RegisterDisplayView.layout.contract.test.ts`) for picker type, TWINT fill/QR size, and customer-display overflow.

## Risks / Trade-offs

- **[Risk] Shared `.sheet--picker .sheet-option-row__control--btn` also styles voucher redeem lists** → Mitigation: if voucher rows must stay compact, scope the inherit/min-height under `LayoutCellPickerSheet` only; prefer shared picker rule if voucher rows should match POS type anyway.
- **[Risk] Hosted-demo wide mode constrains `.sheet` width but not height** → Mitigation: TWINT override is height-only; keep `body.hosted-pi-demo--wide .sheet { width: min(430px, 100vw) }`.
- **[Trade-off] Position wählen with many variants still scrolls inside the picker** — same as Zusätze; footer stays pinned via existing `.sheet--picker` flex.
- **[Trade-off] Operator QR letterboxes** inside `.qr-wrap` when the wrap aspect ratio differs from the TWINT card — expected with `object-fit: contain`.

## Migration Plan

1. Ship Pi frontend CSS/Vue + contract tests.
2. No data migration. Rollback is revert of the frontend change.
