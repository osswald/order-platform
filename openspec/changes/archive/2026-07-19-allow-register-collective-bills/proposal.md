## Why

Cashiers currently get redirected to the waiter login when opening **Sammelrechnungen**, even though the register hub exposes that action and the existing specification requires list, create, open, and settlement parity with waiters. The collective-bill routes only recognize waiter sessions, so valid cash-register sessions cannot enter the flow.

## What Changes

- Allow an active cash-register session or waiter session to access the open collective-bills list.
- Allow either session type to open and settle a collective bill.
- Preserve the existing waiter-login redirect when neither valid operator session is active.
- Keep register-origin navigation context so leaving the collective-bill flow returns to the originating register hub.
- Add router-guard coverage for waiter, register, and unauthenticated access to both collective-bill routes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `register-order-settlement`: Clarify and enforce that cash-register sessions can access, create, open, and settle collective bills with the same capabilities as waiter sessions.

## Impact

- Pi frontend router metadata and route guard authorization semantics.
- Pi frontend router tests and existing collective-bill/register-hub tests.
- No backend API, database schema, dependency, or OpenAPI changes.
