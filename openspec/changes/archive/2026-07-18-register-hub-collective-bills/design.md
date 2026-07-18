## Context

Register payment unification already lets cashiers assign open register lines to a Sammelrechnung from `RegisterPayView`. The waiter hub exposes a dedicated **Sammelrechnungen** entry into `OpenCollectiveBillsView` → `PayCollectiveView`, but the register hub only lists open register orders. Those collective views hardcode back navigation to the waiter `hub` route, so even deep-linking would drop the cashier out of register context.

## Goals / Non-Goals

**Goals:**
- Register hub offers Sammelrechnungen entry equivalent to the waiter hub.
- List, create, open, and settle collective bills from that entry without leaving register context.
- Back navigation from the collective list (and from settle back to the list) returns to the register hub when entered from there.

**Non-Goals:**
- Backend/API changes (open list and settle endpoints already exist).
- Changing assign-from-register-pay semantics.
- Showing collective bills inline on the register hub (a button + shared list is enough).
- Rewording the empty-state “Am Tisch …” assign hint on `PayCollectiveView` (optional polish, not required).
- Instant-mode special casing beyond what the shared list already does (hide “Neue Sammelrechnung” in instant mode).

## Decisions

1. **Reuse `OpenCollectiveBillsView` / `PayCollectiveView`.** Do not fork register-specific collective screens. Alternative: duplicate views under `/register/.../collective` — rejected; doubles maintenance for identical list/settle UX.

2. **Propagate return context via route query.** From the register hub, navigate with something like `query: { returnTo: 'register-hub', registerUuid }`. `OpenCollectiveBillsView` and navigation into `PayCollectiveView` preserve those query params; back actions resolve:
   - register return → `{ name: 'register-hub', params: { registerUuid } }`
   - default → `{ name: 'hub' }` (waiter)

   Alternative considered: infer from `registerSession` in the store — rejected as implicit and brittle if sessions overlap or stale state remains after role switches. Explicit query keeps tests deterministic.

3. **Hub button placement.** Add a full-width hub button on `RegisterHubView` below **Neue Bestellung** (and above the open-orders section), labeled **Sammelrechnungen**, matching waiter hub wording and styling (`btn hub-btn`).

4. **No role gating on the API.** Event-scoped collective bills remain shared; any authenticated Pi client for the event can list/settle. Register entry only unlocks the existing UI path.

## Risks / Trade-offs

- [Query params dropped when opening a bill] → Pass `returnTo` / `registerUuid` through every `router.push` between list and settle; cover with frontend tests.
- [Cashier lands on waiter hub if return context missing] → Default remains waiter `hub` (current behavior); only register entry sets the query.
- [Empty collective bill still shows waiter-centric assign hint] → Acceptable for v1; assign from register pay already works; hint polish can follow.

## Migration Plan

Frontend-only. No schema, sync, or API migration. Deploy with the Pi frontend release; no rollback beyond reverting the UI change.
