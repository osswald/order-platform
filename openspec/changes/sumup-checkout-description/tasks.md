## 1. Description helper (cloud)

- [ ] 1.1 Add failing unit tests for joining event name, Solo label, and waiter name with ` · `, skipping blanks, omitting description when nothing remains, and truncating to 90 characters with an ellipsis
- [ ] 1.2 Implement the helper used by edge checkout create
- [ ] 1.3 Run the new helper tests

## 2. Edge checkout create (cloud)

- [ ] 2.1 Add failing tests: checkout `description` is `{event} · {Solo label} · {waiter}` when `waiter_uuid` matches an event waiter; register-style create without waiter is `{event} · {Solo label}`; unknown waiter uuid omits the waiter part; never `Event {id}`
- [ ] 2.2 Add optional `waiter_uuid` to the edge checkout create schema and resolve `EventWaiter.name` for that event
- [ ] 2.3 Pass the composed description into `create_reader_checkout`; leave `foreign_transaction_id` unchanged
- [ ] 2.4 Export OpenAPI if the edge schema is in the published spec; regenerate cloud frontend types only if that export changes
- [ ] 2.5 Run cloud backend SumUp edge tests

## 3. Pi proxy and POS

- [ ] 3.1 Add failing Pi backend tests that forward optional `waiter_uuid` on checkout create
- [ ] 3.2 Thread `waiter_uuid` through Pi checkout body and `cloud_client.create_sumup_checkout`
- [ ] 3.3 Add failing Pi frontend tests: waiter session sends `waiter_uuid`; no waiter session omits it
- [ ] 3.4 Pass `waiter.value?.uuid` from `createSumupCheckout` / `collectSumupConnectedPayment`
- [ ] 3.5 Run Pi backend edge SumUp tests and Pi frontend SumUp checkout / resolve-payment tests

## 4. Verification

- [ ] 4.1 Run targeted cloud + Pi tests for the touched SumUp checkout path
- [ ] 4.2 Run `./scripts/lint.sh --staged` (or full lint) before commit
