## Context

The Android waiter app loads the Pi frontend in an edge-to-edge WebView. System bar / cutout sizes are exposed as CSS variables (`--safe-top`, `--safe-bottom`, …) via `AndroidInsets`. Non-fullscreen screens inherit top padding from:

```css
html.android-app .app-main:not(.app-main--fullscreen) {
  padding-top: calc(0.75rem + var(--safe-top));
}
```

Fullscreen POS routes (`meta.fullscreen`) zero that padding and rely on `.order-screen` / `.split-pay-screen` to apply insets and fill height with `height: 100%`. That percentage chain breaks when the emulated-printer hosted-demo wrapper only has `min-height` (no definite height), so screens shrink-wrap and leave a large empty void. TWINT QR uses `position: fixed; inset: 0` but only pads `--safe-bottom`, so content sits under the status bar even on a real venue Pi.

## Goals / Non-Goals

**Goals:**

- Fullscreen order and payment screens fill the visible WebView and clear top/bottom system insets on Android.
- TWINT QR (and other full-bleed fixed sheets in payment flows) clear `--safe-top` as well as `--safe-bottom`.
- Behavior correct with and without emulated-printer / hosted-demo shell.
- Preserve existing non-fullscreen layouts that already look correct.

**Non-Goals:**

- Redesigning order/pay UX or changing flex 50/50 panel proportions beyond making fill work.
- Changing Android native inset reporting (bridge already works for normal screens).
- iOS / browser PWA polish beyond what falls out of shared CSS.
- Kitchen / pickup / customer-display fullscreen routes unless the same CSS roots already cover them cheaply.

## Decisions

### 1. Fix viewport fill via a robust height chain (not `position: fixed` for order/pay)

**Choice:** Keep `.order-screen` / `.split-pay-screen` in normal document flow. On `html.android-app`, give every ancestor from `#app` through hosted-demo wrappers a definite `height: 100%` (and `min-height: 0` where flex children need it) so `height: 100%` on the POS roots resolves. Prefer this over making order/pay `position: fixed` so scrolling, sheets, and hosted side-by-side demo layout stay simpler.

**Alternatives considered:**

- `position: fixed; inset: 0` on order/pay — bulletproof height, but fights hosted-demo column width and teleported overlays.
- Revert Android to `100dvh` — previously avoided because dvh ignored system bars in this WebView; only reconsider if paired with explicit inset padding and verified on device.

### 2. Insets on fullscreen roots + full-bleed sheets

**Choice:** Continue putting `--safe-top` / `--safe-bottom` on `.order-screen` / `.split-pay-screen` under `html.android-app` (headers stay compact). Add matching top inset padding to `TwintQrSheet` and audit other `inset: 0` sheets used during payment (payment type picker, receipt prompt) for the same omission.

**Alternatives considered:**

- Only pad `app-main--fullscreen` — would double-pad if screen roots also pad; screen-root padding matches current Android CSS intent.

### 3. Hosted-demo / emulated printer must participate in the height chain

**Choice:** Under `html.android-app`, set `.hosted-demo-shell` and `.hosted-demo-app` to `height: 100%` / flex fill with `min-height: 0`, not only `min-height: 100dvh`.

**Alternatives considered:**

- Special-case `emulatedPrinter` to force `app-shell--fullscreen` — incomplete; wrapper still needs height.

### 4. Verification

**Choice:** Prefer a small CSS/DOM contract test if the suite can assert computed styles under a stub `android-app` class; otherwise document a manual Android checklist (order empty cart, pay with few lines, TWINT sheet, with and without Belege FAB). No backend changes.

## Risks / Trade-offs

- **[Risk] Height rules regress desktop/hosted wide layout** → Scope Android overrides under `html.android-app`; keep wide hosted grid rules intact.
- **[Risk] Double safe-top if both main and screen pad** → Keep `app-main--fullscreen { padding: 0 }` and pad only screen roots / sheets.
- **[Risk] Other fullscreen routes (kitchen, pickup) share CSS roots partially** → Smoke-check; out of primary scope unless broken by the same rules.
- **[Trade-off] Manual device QA still required** — WebView inset behavior is hard to fully unit-test.

## Migration Plan

- Ship as a normal Pi frontend change in the Android-bundled build / Play release pipeline; no data migration.
- Rollback: revert the frontend CSS/component padding commit.

## Open Questions

- None blocking: real-venue TWINT inset bug is confirmed; order/pay fill will be fixed for both demo and non-demo height chains by decision 1+3.
