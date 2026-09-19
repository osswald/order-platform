## Why

During a live event, Pi operational restore’s ghost cleanup deletes local **open** register and table submissions that are not yet in the cloud snapshot — and with them their **kitchen tickets**. Sync often runs restore **before** outbox push, and pending outbox even **forces** a restore check — so Fertig → Bezahlen → Bar can hit `Order not found or not open` / `No open orders for this table`, and the kitchen monitor never shows (or suddenly loses) those orders. Restore then reports `restored_kitchen_tickets: 0` because cloud does not re-invent tickets from lines. This was noted as a follow-up when `pi-operational-restore` was first hardened; it is now breaking money path and kitchen visibility on appliances.

## What Changes

- Ghost cleanup MUST retain local open orders that still have `pending`/`error` outbox rows for their `client_order_id`, even when that id is absent from the cloud open-order list.
- When a restore check will apply a snapshot, the sync cycle MUST push pending submission outbox rows **before** applying restore, so cloud can learn about new opens and local keep-sets stay aligned.
- True ghost deletes (orders not kept) MUST cascade to normalized `order_items` (and existing ticket/pickup/outbox cleanup) so OPEN item rows do not outlive their submission.
- No public API shape changes; register/table settlement contracts stay as today once the open order survives until pay.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `pi-operational-restore`: Add requirements that ghost cleanup never removes unsynced local opens (pending/error outbox), and that purged submissions remove dependent `order_items`.
- `pi-sync-cycle-efficiency`: Require push of pending submission outbox before restore application when a restore check applies a 200 snapshot (ordering change within the existing shared-client cycle).

## Impact

- **Pi backend**: `operational_restore.py` (`_ghost_cleanup_orders` / keep-set assembly), `sync_service.py` (`run_sync_cycle` / `pull_and_restore` ordering); tests in `test_operational_restore.py`, `test_sync_service.py` (and related).
- **Pi frontend / cloud**: none required for the durable fix.
- **Ops**: After deploy, live events should stop losing open Kasse/table orders between Fertig and cash, and kitchen tickets for those orders should remain on the monitor; orphan OPEN `order_items` / already-deleted tickets from prior purges may remain until a separate cleanup (out of scope unless a one-shot migration is added in tasks).
- **Note**: Kitchen monitor tabs only list tickets for printers configured under `kitchen_monitors` (today appliance **70 / Küche**). Getränke-only orders route to station printer 52 and are not expected on the Küche monitor — that is separate from ghost purge.
