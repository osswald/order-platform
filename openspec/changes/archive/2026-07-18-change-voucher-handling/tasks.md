## 1. Backend pricing integrity

- [x] 1.1 Add failing tests that spoofed `unit_cents`, unknown definition UUID, and `article_entitlement` sales are rejected / priced from definition
- [x] 1.2 Change `voucher_sale_unit_cents` to always resolve the event definition and ignore client `unit_cents`
- [x] 1.3 Run Pi backend voucher pricing tests and confirm they pass

## 2. Line groups, selections, and moves

- [x] 2.1 Add failing tests for voucher-sale line groups in order/table/collective summaries and for taking/merging voucher selections by definition UUID
- [x] 2.2 Extend `LineSelection` (and related schemas) so selections can identify voucher-sale groups
- [x] 2.3 Include voucher-sale groups in `_build_line_groups_from_orders` / summary responses
- [x] 2.4 Update `take_selections_from_orders` and `merge_lines_into_list` to move and merge voucher-sale lines by quantity
- [x] 2.5 Run the new line-group/move tests and confirm they pass

## 3. Submission-time voucher printing

- [x] 3.1 Add failing tests that voucher slips are created/returned at order create for register and waiter voucher sales, including open unpaid orders
- [x] 3.2 Move voucher printing to order submission (same create path as station receipts) and stop creating voucher print jobs during settlement/assignment
- [x] 3.3 Add backend support for waiter voucher print payloads and/or explicit network-printer targeting needed by the frontend destination flow
- [x] 3.4 Update/remove obsolete settle-time print expectations; run Pi create/print tests

## 4. Settlement and assignment

- [x] 4.1 Add failing tests: partial voucher settle without reprint; article-only settle leaves vouchers open; collective assign of vouchers allowed; collective settle does not reprint
- [x] 4.2 Remove settle-in-full and assign-collective blocks for voucher-containing orders
- [x] 4.3 Fold voucher payable into shared settle path (`_settle_orders_partial` / order settle) without print-job creation
- [x] 4.4 Ensure redemption credit still applies only to article gross when voucher sales are in the selection
- [x] 4.5 Update/remove obsolete full-settlement rejection tests; run Pi settlement tests

## 5. Waiter voucher sales and printer destination

- [x] 5.1 Add failing tests that unpaid waiter orders with voucher-sale lines create open under pay-later and route to instant collective under instant mode
- [x] 5.2 Remove `Gutscheinverkauf erfordert Zahlung` create-time rejection for waiter orders
- [x] 5.3 Add frontend tests for Bluetooth auto-print, network-printer picker when Bluetooth is absent, and warn-and-continue when no printers are available
- [x] 5.4 Implement waiter submit destination flow using the Android Bluetooth bridge when configured, otherwise prompt for a network printer, otherwise warn and submit
- [x] 5.5 Keep register voucher printing on the register receipt-printer network path
- [x] 5.6 Run Pi voucher create, printing, and order-submit tests

## 6. Pi settle UI

- [x] 6.1 Add/update frontend tests so voucher sales appear as selectable settle rows (not always-due fixed rows) and waiter submit succeeds with unpaid voucher carts
- [x] 6.2 Wire register/table/collective split-pay UIs to unified line groups including voucher sales
- [x] 6.3 Ensure assign-to-collective can include voucher-sale selections
- [x] 6.4 Run Pi frontend tests for cart, split-pay, and order submit

## 7. Verification

- [x] 7.1 Run full Pi backend and Pi frontend test suites
- [x] 7.2 Run `./scripts/lint.sh` for touched areas
