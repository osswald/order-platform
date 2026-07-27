## Context

Cash-register orders today allocate a single event-scoped pickup number, build `pickup_code = {register_prefix}{n}`, store it on `OrderSubmission` / session / payload, and stamp that same code on every station kitchen slip and every customer Abholbeleg. The pickup screen and ready TTL are order-scoped: the order becomes `ready` only when all kitchen tickets are `done`.

Guests with multi-station baskets already receive multiple Abholbelege (one per production-station group). They need distinct codes and independent ready/picked-up lifecycle so Grill can be collected while Bar is still cooking.

Constraints: Pi SQLite operational schema; register prefix and `EventPickupCounter` stay as today; waiter/table flows unchanged; voucher-only register orders still skip pickup slips.

## Goals / Non-Goals

**Goals:**
- One sequential pickup code per production-station group with article lines on a cash-register order
- Independent `pending` → `ready` → `picked_up` per code (and per-code ready TTL)
- Kitchen tickets and Abholbelege carry the station’s code
- Pickup UI/API list tiles per code; register display/pay show all codes; open-orders remains one row listing all codes
- Single-station behaviour indistinguishable from today (one code, same readiness rules)

**Non-Goals:**
- Station-owned prefixes or non-sequential numbering schemes
- Changing waiter/table number flows
- Cloud admin configuration UI
- Splitting the commercial order into multiple payment orders for pickup
- Changing voucher-sale slip behaviour

## Decisions

### 1. Persist station pickups as first-class rows

**Choice:** Add a `station_pickups` (name TBD) table keyed by `local_order_id` + `station_uuid` (nullable station allowed), with `pickup_code`, `pickup_status`, `ready_at`, `picked_up_at`.

**Why:** Pickup list, TTL, and picked-up must query by status independently of the parent order. JSON-only on the order payload is awkward for indexing and concurrent updates when one kitchen ticket completes.

**Alternatives:** Payload-only `pickups[]` — rejected for query/TTL complexity. Split into N `LocalOrder` rows — rejected (breaks payment, open-orders “one row”, settlement).

Also snapshot `pickups[]` (or equivalent) on the order payload for cloud sync / operational restore, mirroring today’s scalar fields.

### 2. Numbering: burn N from the existing event counter

**Choice:** For each station group with article lines, call `_allocate_pickup_number` once and form `{prefix}{n}` with the cash-register `pickup_code_prefix`. Iteration order follows `group_lines_by_station`’s stable group order.

**Why:** Matches current allocator and guest-facing format; no new config.

**Alternatives:** Shared base + suffix (`A1-G`) — rejected as more complex and needs station abbreviations. Station prefixes — out of scope.

Keep `LocalOrder.pickup_code` / session `pickup_code` as the **first** allocated code for compatibility. Expose `pickup_codes: string[]` on create response and register display payloads; open-orders returns `pickup_codes` (UI joins as `A1, A2`) while retaining scalar `pickup_code` = first.

### 3. Readiness is per station pickup, not per order

**Choice:** When a kitchen ticket reaches `done`, mark the matching station pickup `ready` (by `local_order_id` + `station_uuid`). Do **not** wait for sibling stations.

Stations that print directly (no kitchen-monitor ticket for that group) create a station pickup already `ready` at order creation (today’s “no kitchen tickets → ready” behaviour, applied per group).

Partial kitchen print (`Teildruck`) leaves the ticket open → station pickup stays `pending` until the ticket is fully done.

**Order-level `pickup_status`:** Stop driving the pickup screen from it. Optionally keep a derived/legacy value (e.g. `pending` while any station pickup is pending/ready; `picked_up` when all are picked_up) for older sync consumers — prefer documenting payload `pickups[]` as source of truth.

### 4. Pickup API becomes station-pickup scoped

**Choice:**
- `GET /v1/pickup/orders` returns one entry per active station pickup (`pending`/`ready`), including `pickup_id`, `local_order_id`, `station_uuid`, `pickup_code`, `pickup_status`, `ready_at`, …
- Mark picked-up via `POST /v1/pickup/pickups/{pickup_id}/picked-up` (or equivalent). Retire order-id picked-up for the screen (update Pi frontend in the same change).
- Ready TTL (5 minutes) expires each `ready` station pickup independently.

**Why:** Matches independent collection UX. Frontend and backend ship together on the Pi PWA — acceptable **BREAKING** for that local API surface.

### 5. Kitchen ticket display code

**Choice:** Resolve pickup code for a ticket via station pickup (`order` + `ticket.station_uuid`), not the order’s scalar `pickup_code`. When creating the kitchen print job, pass that station’s code into the ESC/POS payload.

Optional denormalized `pickup_code` column on `kitchen_tickets` is unnecessary if lookup is reliable; prefer lookup + payload stamp at print time unless restore needs denormalization.

### 6. Register UX surfaces

| Surface | Behaviour |
|---------|-----------|
| Customer display / pay success | Show all `pickup_codes` |
| Open-orders hub | One row; label lists all codes (`A1, A2`) |
| Create response | `pickup_codes` + legacy `pickup_code` (first) |

### 7. Settlement / restore

Partial settle keeps **all** station pickups on the original open order (same as today’s “pickup stays on original”). Paid split child orders do not own pickups.

Operational restore: recreate station pickups from synced payload when restoring an open register order; do not invent pickups if cloud payload lacks them (align with kitchen restore caution). Detail in implementation tests; no change to restore *policy* beyond honouring the new payload shape.

## Risks / Trade-offs

- **[Risk] Pickup API shape change breaks an old Pi frontend build** → Mitigate: ship backend + frontend together; keep create-response scalar `pickup_code` for older register display clients that only show one code until updated.
- **[Risk] Counter burns faster on multi-station events** → Acceptable; numbers stay unique and short.
- **[Risk] Null / unknown station groups** → Still allocate one pickup for that group; slip may lack a station label (same as today).
- **[Risk] Order-level vs station-level status drift in cloud analytics** → Document `pickups[]` as source of truth; keep first code on order for simple lists.
- **[Trade-off] Extra table vs payload-only** → Table wins for TTL/list correctness at cost of a Pi schema migration.

## Migration Plan

1. Pi Alembic / schema patch: add `station_pickups` table.
2. Deploy Pi backend + frontend together.
3. In-flight orders created before upgrade keep scalar order pickup behaviour until completed; no backfill required for historical orders (or lazy: treat missing station pickups as single synthetic pickup from `LocalOrder.pickup_code` when listing — implement if needed for mid-shift upgrades).

Rollback: revert release; new table unused by old code.

## Open Questions

- None blocking. Optional: mid-shift upgrade compatibility shim for orders that only have scalar `pickup_code` (recommend yes: synthesize one virtual pending/ready pickup from order fields when listing).
