## 1. Authorization Tests

- [x] 1.1 Add failing router-guard tests proving an active cash-register session can access both `collective-open` and `pay-collective`.
- [x] 1.2 Add or update router-guard tests proving waiter access remains allowed and sessions without either operator type are redirected with the requested route preserved.
- [x] 1.3 Confirm an active cash-register session remains blocked from unrelated `requiresWaiter` routes.

## 2. Router Authorization

- [x] 2.1 Add a typed route-meta flag for routes that accept either waiter or cash-register sessions.
- [x] 2.2 Update the global router guard to authorize the new operator requirement from session state and preserve the existing unauthenticated redirect contract.
- [x] 2.3 Apply the operator requirement to both the collective-bill list and settlement routes without changing other waiter-only routes.

## 3. Verification

- [x] 3.1 Run the focused router and collective-bill/register-hub tests.
- [x] 3.2 Run all project test suites required by the repository workflow.
- [x] 3.3 Run `./scripts/lint.sh` and resolve any introduced issues.
