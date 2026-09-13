## Why

SumUp Merchant Sales currently shows `Event {id}` (for example `Event 11`) as the checkout description for every connected card payment at that event. Operators cannot tell which event, Solo, or waiter took the payment when reconciling in SumUp.

## What Changes

- Send a human-readable SumUp checkout `description` built from **event name**, **Solo reader label**, and **waiter name** when known.
- Omit missing parts instead of placeholders (`Event 11`, empty slots).
- Truncate the joined string so it remains usable in SumUp’s Merchant Sales column (about 90 characters).
- Existing SumUp rows are unchanged; only new checkouts pick up the new description.
- **Out of scope:** `foreign_transaction_id` / `client_order_id` / other SumUp transaction identifiers.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `sumup-cloud-payments`: Connected Solo checkouts SHALL set SumUp `description` from event name, Solo label, and waiter name (when present), not `Event {id}`.

## Impact

- Cloud edge checkout create: compose `description` from `Event.name`, stored Solo `label`, and waiter name when the POS supplies a waiter identity.
- Pi POS: pass waiter identity on checkout create when a waiter session exists (register-only pays have no waiter).
- Tests around `create_reader_checkout` / edge checkout body.
- No OpenAPI change for cloud admin UI; edge checkout request may gain an optional waiter field.
- SumUp Affiliate Key / `foreign_transaction_id` behaviour is unchanged.
