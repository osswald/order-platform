## Why

Cashiers can assign open register lines to a Sammelrechnung from the payment screen, but the register hub has no entry to list, open, or settle those bills — unlike the waiter hub's "Sammelrechnungen" button. Once lines leave a register order, the cashier cannot follow up without switching into the waiter flow.

## What Changes

- Add a **Sammelrechnungen** action on the cash register hub that opens the same open-collective-bills screen waiters use.
- Make collective-bill list / create / settle navigation work when entered from the register hub (back navigation returns to the register hub, not the waiter hub).
- Keep existing assign-from-register-pay behavior unchanged; this change only closes the hub browse/settle gap.

## Capabilities

### New Capabilities

<!-- None — this extends the existing register settlement capability. -->

### Modified Capabilities

- `register-order-settlement`: Require the register hub to expose Sammelrechnungen entry and return-path parity with the waiter hub, so cashiers can list, create, and settle open collective bills without leaving the register context.

## Impact

- Pi frontend: `RegisterHubView.vue` (new hub button), `OpenCollectiveBillsView.vue` and `PayCollectiveView.vue` (context-aware back navigation to register hub vs waiter hub), possibly router query/params or a small composable for "return to hub".
- Pi frontend tests: `RegisterHubView.test.ts` and collective-bill view tests for back navigation.
- No Pi/cloud backend API changes — `GET /v1/collective-bills/open` and settle endpoints already serve both roles.
- No OpenAPI regeneration required.
