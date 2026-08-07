## Why

Physical event dry-runs need realistic order volume against real printers, kitchen monitors, and drawers — not just connectivity Testdruck. Today operators can only place orders by hand, which cannot simulate several waiters posting simultaneously or sustain minute-scale bursts. A guarded load-test tool on the Pi lets hire-company/ops stress an event in `test` status before doors open.

## What Changes

- Add a **Lasttest** admin tool under Pi Admin → Betrieb that configures and runs a volume simulation against the selected event.
- Config: waiter count, cash register count, table range, total order count (capped by real event waiters/registers).
- Backend asyncio job places synthetic orders through the real create → settle path (cash), using the event’s articles, stations, waiters, and registers.
- Cadence: one concurrent burst per minute (all configured actors fire together), then wait until the next minute; each actor ≈ 1 order/min.
- Baskets: 1–8 people; articles from 1..n randomly chosen stations; additions attached sometimes with weight toward `preselected`.
- After settle: network-print payment receipt ~30% of the time; cash drawer kicks on register cash settles; station/kitchen/customer slips behave like any other order (kitchen print remains manual).
- Hard gate: only for events with `status === "test"` (UI + API); single-flight; in-memory progress only (no persist, no cleanup CTA).
- Frontend shows start/stop and live progress (placed, failed, receipts printed, burst counters).

## Capabilities

### New Capabilities
- `pi-admin-load-test`: Pi Admin Lasttest volume simulator — config UI, backend job, hard `test`-only gate, concurrent burst order generation with settle and probabilistic payment-receipt print.

### Modified Capabilities
- _(none)_

## Impact

- **Pi backend**: new load-test module (asyncio job + module state), HTTP start/status/stop routes, reuse create/settle/receipt/print and cash-drawer side effects; reject non-`test` events.
- **Pi frontend**: new Admin → Betrieb tile + view; poll progress; gate tile/form on `isEventTest`.
- **Tests**: backend job/API/gate/basket generation; frontend view and gate behavior.
- **Out of scope**: cloud UI, purge/cleanup tooling, job persistence across restarts, SumUp/Twint settle paths, auto kitchen print.
