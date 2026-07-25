## 1. Regression tests first

- [x] 1.1 Add an event-transactions API test with a persisted order line missing `article_id`; assert HTTP 200, empty line details, zero `line_cents`, and preserved payment fields
- [x] 1.2 Add a mixed valid/malformed line test; assert the valid line alone determines `lines`, `line_count`, and `line_cents`
- [x] 1.3 Add malformed numeric identifier/quantity/addition cases and assert they do not hide other transaction rows

## 2. Defensive transaction rendering

- [x] 2.1 Add a transaction-specific line validation/filter helper that catches only expected payload conversion errors
- [x] 2.2 Use the same filtered line list for detail formatting, line count, and total calculation
- [x] 2.3 Emit a payload-safe warning with event/order identity and skipped-line count

## 3. Verification

- [x] 3.1 Run the event transaction/report test modules and the full cloud backend test suite
- [x] 3.2 Run `./scripts/lint.sh` and confirm no OpenAPI regeneration is needed
- [x] 3.3 Re-check the malformed demo order through `GET /events/{event_id}/transactions` and confirm HTTP 200
