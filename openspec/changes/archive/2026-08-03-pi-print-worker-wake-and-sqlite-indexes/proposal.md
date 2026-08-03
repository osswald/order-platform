## Why

After deferring ESC/POS render off the HTTP path and lightening sync, the Pi print worker still polls SQLite every second and runs Pillow/ESC/POS **on the FastAPI event loop**, so busy kitchens can stall money-path requests while idle appliances burn needless wakeups. Separately, migrated Pi databases lack indexes that models imply for hot filters (`print_jobs.status`, open orders, outbox, kitchen tickets), so scans and lock time grow with event size.

## What Changes

- Wake the print worker promptly when jobs are enqueued or retried (instead of only the fixed 1s poll), with a bounded idle wait as fallback
- Run deferred ESC/POS payload build (`ensure_print_job_payload` / render context) off the event loop (e.g. thread pool) so HTTP/sync stay responsive during print bursts
- Keep durable `queued` → render → send semantics and crash/retry behaviour from `pi-receipt-render-offload`
- Add Alembic indexes (and align ORM) for hot SQLite filters used by the print worker, open-order lists, sync outbox, and kitchen ticket queries
- **Out of scope:** Redis; changing print job kinds or HTTP contracts; eliminating full-bundle stock SD rewrites; chunked cloud bundle pull

## Capabilities

### New Capabilities
- `pi-print-worker-scheduling`: Wake-on-enqueue and off-event-loop render for the Pi print worker
- `pi-sqlite-hot-path-indexes`: Durable SQLite indexes for Pi hot-path filters (print queue, open orders, outbox, kitchen)

### Modified Capabilities
- _(none — `pi-receipt-render-offload` remains binding for deferred network PrintJobs)_

## Impact

- **Pi backend**: `print_worker.py`, enqueue/retry call sites (`edge_common`, kitchen, print-jobs retry, shift paths as needed), `models` / `models_operational`, new Alembic revision after `007_synced_bundle_etag`, tests
- **APIs / OpenAPI**: none
- **Ops**: one-time index build on upgrade (SQLite); slightly higher insert cost on indexed columns
- **Related**: complements receipt-render offload (worker now owns heavy render) and sync-cycle efficiency (less lock fight when scans are indexed)
