## Why

An event can outlast a single cash shift, and the same waiter or cash register may open and close multiple shifts during one event. Today the Pi allows sequential shifts locally, but cloud upserts by `subject_key` (`waiter:{uuid}` / `cash_register:{uuid}`), so each new shift overwrites the previous one in admin reporting. Operators need a durable log of every shift for the event.

## What Changes

- Mint a stable `cash_session_uuid` when a shift opens (waiters and cash registers alike).
- Keep the operational rule: at most one **OPEN** shift per subject per event.
- Change cloud ingest so each shift is stored and listed as its own row (upsert by org + event + `cash_session_uuid`), not by subject alone.
- Keep `subject_key` as a non-unique attribute for “who” and for open-session restore filtering.
- Surface all synced shifts in the existing cloud event Schichten (cash sessions) admin list.
- **Forward-only:** no backfill of shifts already overwritten in cloud; no new export/PDF surfaces in this change.

## Capabilities

### New Capabilities

- `cash-shift-session-history`: Multi-shift cash session identity, sync, and cloud admin history for waiters and registers within an event (one open at a time; all closed/open instances logged).

### Modified Capabilities

- (none — restore kitchen/order rules unchanged; open cash-session restore continues to select OPEN by subject, now without erasing closed history)

## Impact

- **Pi backend:** `CashSession` model + open path; sync payload includes `cash_session_uuid`; local integer id remains for ledger FKs.
- **Cloud backend:** `EdgeCashSession` unique constraint and upsert; operational snapshot still exports OPEN sessions by subject; event cash-sessions list returns multiple rows per waiter/register.
- **Cloud frontend:** Schichten tab already lists rows — verify multi-row display; no new screens.
- **Pi frontend:** no UX change required beyond existing open-after-close flow.
- **Tests:** Pi open second shift after close; cloud upsert retains both; restore still finds the single OPEN by subject.
