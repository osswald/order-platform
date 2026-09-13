## Context

See proposal.md for motivation. Today `POST /edge/v1/sumup/checkout` always sends `description=f"Event {event.id}"`. Event name and Solo label are already on the cloud at create time (`Event`, `SumupReader`). Waiter name is only on the Pi session (`waiter.uuid` / `waiter.name`) and is not on the checkout body.

SumUp Cloud API `description` has no documented max length; Merchant Sales is a short column. Online checkout `checkout_reference` is capped at 90 characters — use that as the practical budget.

`foreign_transaction_id` / `client_order_id` stay as they are.

## Goals / Non-Goals

**Goals:**
- Compose description on the cloud from event + Solo label + optional waiter.
- Thread waiter identity from POS → Pi proxy → cloud checkout create.
- Unit-test join/omit/truncate without calling SumUp.

**Non-Goals:**
- Changing Affiliate Key / `foreign_transaction_id` / `client_order_id`.
- Putting cash-register name in the description.
- Rewriting historical SumUp sales rows.
- Showing this string in Vendiqo admin UI.

## Decisions

1. **Compose on the cloud, not the Pi**  
   Event name and Solo label are authoritative in cloud DB (`Event.name`, `SumupReader.label` for the requested `reader_id`). The POS already sends `reader_id`; `_reader_for_org` already loads that row.  
   Alternative: Pi sends a pre-built string — rejected, labels can drift from the session copy.

2. **Pass `waiter_uuid`, look up name on cloud**  
   Optional `waiter_uuid` on the edge checkout body. Cloud resolves `EventWaiter.name` for that event. Unknown/missing uuid → omit waiter.  
   Alternative: POS sends the display name — rejected, uuid is the session source of truth and stays consistent with order payloads.

3. **Join format ` · `**  
   Same separator the POS already uses in event lists. Skip blank parts after strip. Order: event, Solo label, waiter. Register pays typically yield `Dorffest · Bar`.

4. **Hard cap 90 characters**  
   Truncate the joined string (character length, keep a trailing ellipsis when cut). Prefer clipping the end so event name survives longest.

5. **No fallback to `Event {id}`**  
   If every part is empty after strip, omit `description` rather than revive the numeric id. Event name is required in our model, so this is a defensive edge case.

6. **Thread the field through Pi proxy**  
   `SumupCheckoutBody`, `create_sumup_checkout` in `cloud_client`, and Pi `createSumupCheckout` gain optional `waiter_uuid` from `waiter.value?.uuid`. Register/split-pay with no waiter session omit it.

## Risks / Trade-offs

- **[Risk] SumUp UI still clips under 90** → Mitigation: 90 is a budget, not a guarantee; event-first join keeps the most useful prefix.
- **[Risk] Waiter renamed mid-event after session start** → Mitigation: resolve name at checkout time from `EventWaiter`, not the possibly stale session name.
- **[Risk] Edge OpenAPI / Pi types drift** → Mitigation: add the optional field on cloud and Pi schemas; regenerate types if the export includes edge checkout.

## Migration Plan

Deploy cloud before or with Pi. Old Pis omit `waiter_uuid`; cloud still sends `event · Solo`. No data migration. Rollback restores `Event {id}` on new checkouts only.
