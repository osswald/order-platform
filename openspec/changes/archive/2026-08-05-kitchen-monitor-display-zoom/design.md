## Context

Kitchen tickets use CSS multi-column layout with a minimum column width (~260px). On typical tablet landscape widths, that yielded too few columns. Manual browser zoom to 80% looked correct to venue staff.

## Goals / Non-Goals

**Goals:**

- Match ~80% browser zoom density on the kitchen monitor route.
- Fit at least four order columns on ~1024 CSS px tablet landscape under that zoom.
- Keep ticket chrome readable (scale via zoom rather than one-off font hacks).

**Non-Goals:**

- Changing pickup / customer-display density.
- User-configurable zoom control.
- Changing kitchen print or ticket business logic.

## Decisions

### 1. CSS `zoom: 0.8` with compensating size

- **Choice**: On `.kitchen-monitor`, set `--kitchen-zoom: 0.8`, `zoom: var(--kitchen-zoom)`, `width/height: calc(… / var(--kitchen-zoom))`.
- **Why**: Closest match to validated browser zoom; scales fonts, padding, and columns together. Compensating size keeps the visual viewport filled.
- **Alternative**: Lower min column width only — rejected (tickets stay visually oversized).

### 2. Keep min column width at 260px; gap 6px

- **Choice**: Leave `KITCHEN_MIN_COLUMN_WIDTH_PX = 260`; set `KITCHEN_ORDER_GAP_PX = 6` and bind CSS `--order-gap` from that constant.
- **Why**: Zoom supplies effective layout width (`viewport / 0.8`); gap tweak addresses the separate “less spacing” request without shrinking ticket content twice.

## Risks / Trade-offs

- **[Risk] `zoom` support** → Mitigation: Chromium/Android WebView (primary kitchen path) supports CSS zoom; Safari kitchen use is secondary.
- **[Trade-off]** Fixed 80% may be tight on very small tablets or loose on large TVs — acceptable default; no in-UI control in this change.

## Migration Plan

Ship Pi frontend (and Android APK if bundled). No data migration. Rollback by reverting the zoom CSS and gap constant.
