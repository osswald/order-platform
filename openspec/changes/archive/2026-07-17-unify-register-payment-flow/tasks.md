# Tasks: Unify Register Payment Flow

## 1. Backend tests (tests first)

- [x] 1.1 Write tests for open register creation: no payments → `payment_status = "open"`, pickup code allocated, print jobs/kitchen tickets created, no receipt; paid creation unchanged; voucher-sale lines allowed open
- [x] 1.2 Write tests for `GET /v1/orders/{id}/summary` (open order, 404 for paid/unknown)
- [x] 1.3 Write tests for `POST /v1/orders/{id}/settle-partial`: full settle, split settle, voucher redemption, voucher-sale full-payment rule with slip printing, cash-drawer kick at settle
- [x] 1.4 Write tests for `POST /v1/orders/{id}/assign-collective` and `GET /v1/registers/{uuid}/open-orders`

## 2. Backend implementation

- [x] 2.1 Relax `create_local_order`: optional payments for registers, explicit open status, drop voucher-sale payment requirement for open register orders, snapshot `item_count` into payload
- [x] 2.2 Add `GET /v1/orders/{id}/summary` via `_summary_from_orders`
- [x] 2.3 Add `POST /v1/orders/{id}/settle-partial` on `_settle_orders_partial` with register settlement meta (drawer kick via existing receipt path), voucher-sale full-settle rule and slip printing
- [x] 2.4 Refactor `settle_table_partial` to delegate to `_settle_orders_partial`
- [x] 2.5 Extract shared assign-collective helper; add `POST /v1/orders/{id}/assign-collective`
- [x] 2.6 Add `GET /v1/registers/{register_uuid}/open-orders` + Pydantic schemas

## 3. Frontend

- [x] 3.1 Extract `SplitPaySettleScreen.vue` from `PayTableView`/`PayCollectiveView`; convert both to thin wrappers
- [x] 3.2 Extend `PayTableActionsSheet` with `assignPath` prop and transfer-hiding flag
- [x] 3.3 Create `RegisterPayView.vue` (summary/settle endpoints, TWINT display mirroring, receipt to register printer, pickup display payload on full settle); add `register-pay` route
- [x] 3.4 RegisterOrderView: remove voucher redemption UI and payment step; submit open order and navigate to `register-pay`; extract shared submit plumbing with `OrderView`
- [x] 3.5 RegisterHubView: open-orders list with tap-to-resume

## 4. Verification

- [x] 4.1 Run pi backend test suite (and cloud backend suite as regression)
- [x] 4.2 Run pi frontend tests and typecheck; adapt affected tests
- [x] 4.3 Run `./scripts/lint.sh`
