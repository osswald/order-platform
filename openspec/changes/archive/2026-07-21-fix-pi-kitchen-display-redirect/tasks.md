## 1. Failing tests first

- [x] 1.1 Add router guard tests: kitchen URL with valid `?event=` and no waiter/register session allows navigation and sets `selectedEventId`; missing/invalid `event` with null selection redirects to `events`
- [x] 1.2 Add `useAdminOperations` tests asserting kitchen URL builders include `event` from `opsEventId` for copy/open paths
- [x] 1.3 Run the new tests and confirm they fail before implementation

## 2. URL builders and guard restore

- [x] 2.1 Update `kitchenUrlForSlug` (and any related helpers) to append `event` from the selected operations event
- [x] 2.2 In `setupRouterGuards`, before the `requiresEvent` check, restore `selectedEventId` from `to.query.event` when it is a valid id in the ready bundle; do not write waiter/register session storage
- [x] 2.3 Optionally apply the same `?event=` query to register-display / pickup URL builders opened via `window.open` if they share the failure mode

## 3. Verify and document

- [x] 3.1 Run Pi frontend tests (`cd pi/frontend && npm test`) and ensure all pass
- [x] 3.2 Update `pi/README.md` kitchen monitor URL note to include `?event=<id>`
- [x] 3.3 Run `./scripts/lint.sh --staged` (or full lint for touched areas) before commit
