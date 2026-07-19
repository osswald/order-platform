## Context

The Pi frontend has mutually exclusive waiter and cash-register sessions. The collective-bill list and settlement routes currently declare `requiresWaiter`, so the global router guard redirects a cashier to the waiter login before either view can use the register return context already passed by `RegisterHubView`.

The collective-bill views and APIs operate on the selected event and do not require waiter-specific identity. A cash-register shift is already established when entering the register hub. The change is therefore limited to frontend route authorization and its tests.

## Goals / Non-Goals

**Goals:**

- Treat a waiter session or cash-register session as a valid operator session for collective-bill list and settlement routes.
- Preserve waiter behavior and register-origin back navigation.
- Keep unauthenticated access blocked.
- Cover authorization behavior with router-guard tests before implementation changes.

**Non-Goals:**

- Changing collective-bill APIs, settlement semantics, or shift accounting.
- Allowing cash-register sessions into other waiter-only routes.
- Changing the mutually exclusive waiter/register session model.
- Changing which actions are available in instant payment mode.

## Decisions

### Introduce route-level operator authorization

The two collective-bill routes will use a dedicated route meta requirement representing “waiter or cash register.” The router guard will satisfy it when either `store.waiter` or `store.registerSession` is active.

This keeps authorization explicit in route metadata and avoids broadening `requiresWaiter`, whose meaning remains unchanged for waiter-only flows such as tables, stock, and waiter orders.

**Alternative considered:** Make `requiresWaiter` accept cash-register sessions globally. Rejected because it would unintentionally authorize register sessions for every waiter-only route.

### Do not authorize from return query parameters

The guard will inspect session state only. `returnTo=register-hub` and `registerUuid` remain navigation context, not evidence of authorization.

**Alternative considered:** Exempt collective routes from waiter checks when register return query parameters are present. Rejected because query parameters are user-controlled and can become stale; the existing register session is the authoritative state.

### Keep the existing unauthenticated destination

When neither session exists, operator-protected collective routes will continue to redirect to the waiter login with the requested URL in `redirect`. This preserves current behavior for ordinary unauthenticated entry and avoids adding a new operator-selection route in this focused fix.

## Risks / Trade-offs

- **Risk:** A future operator-protected route could need a different unauthenticated destination. → Keep the new meta narrowly applied to the two collective-bill routes and test its current redirect contract.
- **Risk:** One of the routes is updated without the other, allowing list access but failing at settlement. → Test and update both `collective-open` and `pay-collective`.
- **Trade-off:** The meta name adds another authorization concept. → The explicit concept prevents accidental access expansion across existing waiter-only routes.
