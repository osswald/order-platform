## Why

Operational restore on the Pi can resurrect finished kitchen tickets and reopen settled (or partially settled) tables when a later sync cycle applies a stale cloud open-order mirror. Creating new local orders often triggers the fingerprint mismatch that runs restore — so staff see “old” tickets reappear on the kitchen monitor and tables look unpaid again. That must not happen on a live appliance.

## What Changes

- Protect local kitchen completion: if an order already has kitchen tickets and all are `done`, restore MUST NOT delete, rewrite, or regenerate those tickets.
- Stop inventing kitchen work when the cloud kitchen snapshot is empty: restore MUST NOT fall back to regenerating open tickets from order lines solely because cloud sent no tickets.
- Protect local settlement: restore MUST NOT reopen a locally `paid` order from a cloud open payload, and MUST NOT clobber a locally progressed open order (e.g. fewer lines after partial settle) with an older fuller cloud payload when local is clearly ahead.
- Prefer local durability when pending outbox exists for that order: do not restore kitchen/order state over unsynced local settlement or kitchen-done updates.
- Keep appliance takeover (empty local SQLite) working: cloud open orders and cloud kitchen tickets still restore when there is no conflicting local completion/settlement signal.
- Add regression tests for the resurrection scenarios (done kitchen + empty cloud kitchen; paid local + open cloud; partial-settle local vs stale cloud lines).

## Capabilities

### New Capabilities

- `pi-operational-restore`: Rules for when cloud operational snapshot restore may rewrite local open orders and kitchen tickets, and when local completion/settlement must win so finished work and payments do not resurrect on a live Pi.

### Modified Capabilities

- (none)

## Impact

- **Pi backend**: `operational_restore.py` (order + kitchen restore paths), possibly fingerprint/`needs_operational_restore` helpers; tests under `pi/backend/tests/test_operational_restore.py` (and related kitchen/sync tests as needed).
- **Sync cycle**: behavior change only in restore application; pull-before-push order can remain for this change (optional follow-up).
- **Cloud**: no API/schema change required; mirror already deletes kitchen snapshots when all tickets are done and order snapshots when paid.
- **Pi/Cloud frontends**: none.
- **Takeover (scenario B)**: still supported when local has no paid/all-done conflict; empty-cloud-kitchen + open order on a blank Pi will no longer invent kitchen tickets (kitchen stays empty until new local orders create them).
