## Context

Station-scoped pickups (`#226`) allocate one pickup code per production-station group on cash-register orders, persist `station_pickups`, and stamp each customer Abholbeleg with that station’s code. Kitchen monitor list/serialize resolves the code via `payload.pickups[]` (and order scalar as fallback) — that path is correct.

Station and kitchen **PrintJobs** go through `_create_print_job_for_lines`, which accepts `pickup_code` but only uses it for printer routing. The render context is built from `{**order.payload, lines: ...}` without overwriting `pickup_code`. At order create, order payload still has `pickup_code: null`, so direct station slips omit the hero. After sync, scalar `pickup_code` is the first allocated code, so kitchen-monitor prints of a later station stamp the wrong code.

Customer pickup already does the right thing in `_create_customer_pickup_print_job_for_lines`.

## Goals / Non-Goals

**Goals:**
- Station `station_order` and `kitchen_ticket` PrintJob render payloads carry the station-scoped pickup code passed into job creation.
- Direct-print and kitchen-monitor print paths both show that code on the slip hero.
- Regression tests for multi-station cases where the kitchen station is not the first code.

**Non-Goals:**
- Changing allocation, `station_pickups`, pickup screen, or kitchen list/UI resolution.
- Changing waiter/table flows.
- Cloud admin or OpenAPI surface changes.
- Denormalizing pickup code onto `kitchen_tickets` rows.

## Decisions

### 1. Stamp in `_create_print_job_for_lines` only

**Choice:** When `pickup_code is not None`, set `station_payload["pickup_code"] = pickup_code` before `make_render_context`, mirroring customer pickup.

**Why:** Single chokepoint for all station/kitchen network PrintJobs (order create direct print, kitchen full/partial print). Callers already pass the correct station code.

**Alternatives:** Patch each caller to mutate `payload` before calling — rejected (easy to miss, duplicates customer-pickup pattern). Fix only kitchen enqueue — rejected (leaves direct-print gap).

### 2. Keep caller-side resolution as-is

**Choice:** Continue passing `station_pickup_code` from order create and `_pickup_code_for_station(...)` from kitchen print; do not change serialize/list.

**Why:** Display already works; bug is render payload only.

### 3. Tests assert rendered slip / render context text

**Choice:** Extend Pi backend tests to decode `station_order` / `kitchen_ticket` jobs (via `ensure_print_job_payload`) and assert the station code appears (and the sibling station’s code does not as the hero for that job). Include a case where the kitchen-monitor station is the second allocated code.

**Why:** Existing tests only checked `customer_pickup` jobs and kitchen *list* JSON, which is why this shipped.

## Risks / Trade-offs

- **[Risk] Callers that intentionally omit `pickup_code` rely on payload** → Mitigation: only overwrite when kwarg is not `None`; waiter table heroes unchanged.
- **[Risk] Pre-rendered / already-queued jobs on a live Pi keep wrong payloads until drained** → Acceptable; new jobs after deploy are correct. No migration of queued jobs.
- **[Trade-off] Spec delta clarifies print-job scenarios rather than inventing a new capability** → Keeps archive merge into `station-scoped-pickups`.

## Migration Plan

1. Land Pi backend fix + tests via PR.
2. Deploy Pi backend (frontend unchanged).
3. Rollback: revert PR; behaviour returns to current (wrong/missing codes on station slips).

## Open Questions

- None blocking.
