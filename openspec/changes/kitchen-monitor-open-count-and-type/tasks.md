## 1. Tests

- [x] 1.1 Add failing `KitchenMonitorHeader` tests: title shows `{station} · {n} offen` for a positive count and for `0`; event name still renders
- [x] 1.2 Add failing `KitchenTicketColumn` tests: table ticket (no pickup code) shows table-chair icon with sky color; pickup ticket shows takeout-box icon with violet color; location text still present; ticket header padding / column-gap constants unchanged

## 2. Implementation

- [x] 2.1 Add a tiny Pi helper with the two official MDI path strings (`table-chair`, `food-takeout-box`) and the locked hex colors (`#38bdf8` / `#c084fc`)
- [x] 2.2 Pass `orders.length` into `KitchenMonitorHeader` and render `{stationLabel} · {n} offen` in the title row (keep event name muted)
- [x] 2.3 On `KitchenTicketColumn`, put the type icon on the existing title line (flex, no extra padding/row); pickup iff `pickup_code`; keep `Tisch` / `Pickup` text
- [x] 2.4 Make the new header and ticket tests pass

## 3. Verify

- [x] 3.1 Run Pi frontend kitchen component tests (`KitchenMonitorHeader.spec.ts`, `KitchenTicketColumn.spec.ts`) and lint staged files
