## 1. Tests first

- [x] 1.1 Add a Pi frontend test (or style contract helper) that stubs `html.android-app` + `--safe-top` / `--safe-bottom` and asserts fullscreen POS roots and TWINT sheet padding/height expectations where practical
- [x] 1.2 Document a short manual Android QA checklist covering order, pay-table, TWINT, and waiter hub (non-regression) with and without emulated printer

## 2. Viewport height chain

- [x] 2.1 Under `html.android-app`, give `.hosted-demo-shell` and `.hosted-demo-app` a definite height/flex fill (`height: 100%`, `min-height: 0`) so fullscreen `height: 100%` resolves with Belege/demo shell
- [x] 2.2 Verify `.app-shell` → `.app-main--fullscreen` → `.order-screen` / `.split-pay-screen` height chain without hosted-demo still fills the viewport
- [x] 2.3 Confirm wide hosted-demo grid layout is unaffected

## 3. Safe-area on fullscreen surfaces

- [x] 3.1 Keep or adjust Android rules so `.order-screen` / `.split-pay-screen` apply `--safe-top` and `--safe-bottom` without double-padding headers
- [x] 3.2 Add `--safe-top` (with existing `--safe-bottom`) to `TwintQrSheet` padding
- [x] 3.3 Audit other payment-flow `position: fixed; inset: 0` sheets (e.g. payment type picker, receipt prompt) and apply the same top inset where missing

## 4. Verification

- [x] 4.1 Run Pi frontend tests and `./scripts/lint.sh` (or staged lint) for touched files
- [ ] 4.2 Manual Android check: order (empty cart), pay-table (few lines + Rest at bottom), TWINT QR, hub still OK — Play Review Demo and ideally real venue Pi (see `qa-android.md`)
