## 1. Tests first

- [x] 1.1 Add a Vitest component test for `KitchenTicketColumn` that mounts a ticket and asserts both **Teildruck** and **Komplettdruck** labels are present in the DOM
- [x] 1.2 Extend that test to cover Teildruck disabled without selection and enabled when a line is selected; assert partial/complete emits on click
- [x] 1.3 Assert action-row CSS contract in the component (or extracted style helpers): two-column tracks use `minmax(0, …)` (or equivalent shrink-friendly rule) and `.action-btn` allows shrink/wrap (`min-width: 0`, `white-space: normal`)

## 2. Safari-safe ticket action styles

- [x] 2.1 Update `.ticket-actions` in `KitchenTicketColumn.vue` to `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)`
- [x] 2.2 Update `.action-btn`: `min-width: 0`, `white-space: normal`, tighter horizontal padding than global `.btn`, and `appearance` / `-webkit-appearance: none`
- [x] 2.3 Keep labels, disabled rules, colors, and emit wiring unchanged

## 3. Verify

- [x] 3.1 Run Pi frontend tests (`cd pi/frontend && npm test` via project npm helper as usual)
- [x] 3.2 Run lint for touched areas (`./scripts/lint.sh --staged` or full as appropriate)
- [ ] 3.3 Manually confirm on iPad Safari (iPadOS 16.x if available): both labels readable, buttons not oversized/clipped; spot-check Chrome desktop unchanged
