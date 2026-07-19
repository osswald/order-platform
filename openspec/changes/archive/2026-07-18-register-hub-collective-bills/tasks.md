## 1. Tests first

- [x] 1.1 Add failing `RegisterHubView` test: Sammelrechnungen button navigates to `collective-open` with register return query (`returnTo` / `registerUuid`)
- [x] 1.2 Add failing tests for `OpenCollectiveBillsView`: back navigates to `register-hub` when return query is present; defaults to waiter `hub` otherwise; opening/creating a bill preserves return query on `pay-collective`
- [x] 1.3 Add failing test for `PayCollectiveView`: back navigates to `collective-open` while preserving return query

## 2. Register hub entry

- [x] 2.1 Add Sammelrechnungen hub button on `RegisterHubView` that pushes `collective-open` with register return context
- [x] 2.2 Confirm open-orders list and existing hub actions remain unchanged

## 3. Shared collective navigation

- [x] 3.1 Teach `OpenCollectiveBillsView` to resolve hub back-target from return query (register hub vs waiter hub) and pass the query into `pay-collective` navigations
- [x] 3.2 Teach `PayCollectiveView` to return to `collective-open` with the same return query preserved
- [x] 3.3 Make waiter entry (no return query) keep today’s back-to-`hub` behavior

## 4. Verify

- [x] 4.1 Run Pi frontend tests (`cd pi/frontend && npm test`) and fix failures
- [x] 4.2 Run staged lint (`./scripts/lint.sh --staged`) before commit
