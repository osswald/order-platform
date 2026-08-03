## Why

On the Pi, order submit (and other money-path actions that enqueue network print jobs) currently builds full ESC/POS payloads inline — including Pillow logo decode, LANCZOS resize, and a per-pixel Python threshold — before the HTTP response returns. Multi-station cash-register orders pay that cost multiple times for the same event logo. That CPU sits on waiter/register “FERTIG” latency on constrained ARM hardware even though the bytes are only needed when the print worker later talks to the printer.

## What Changes

- Cache prepared receipt-logo rasters in-process (keyed by logo content + target width) so repeated slips reuse work
- Replace the slow per-pixel Pillow `point(lambda …)` threshold with a vectorized (or equivalent fast) path without changing logo visual contracts from `escpos-receipt-logo`
- Defer ESC/POS byte generation for **queued network `PrintJob`s** off the request path: enqueue a render context, commit the order, return; the print worker renders (using the logo cache) then sends
- Keep synchronous ESC/POS build for responses that must return payloads to the client (Bluetooth voucher slips, Bluetooth payment-receipt preview/payload APIs, printer test endpoints)

## Capabilities

### New Capabilities
- `pi-receipt-render-offload`: Deferred network print-job rendering and in-process receipt-logo raster cache on the Pi backend

### Modified Capabilities
- _(none — `escpos-receipt-logo` paper-width and placement contracts remain binding; this change must preserve them)_

## Impact

- **Pi backend**: `escpos_render.py` (logo prep/cache), `print_worker.py` (render-then-send), `edge_common.py` / order-create and payment helpers that enqueue `PrintJob`s, `models.py` / Alembic (render-context storage for pending jobs), tests under `pi/backend/tests/`
- **APIs**: `POST /v1/orders` and other enqueue paths still return print job ids; Bluetooth `voucher_escpos_payloads` and payload-returning endpoints stay sync
- **Out of scope**: Bundle JSON caching, sync-worker HTTP reuse, SQLite index migrations, print-worker poll interval, frontend Bluetooth printing UX
