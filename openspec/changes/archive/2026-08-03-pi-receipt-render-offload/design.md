## Context

See proposal.md for motivation. Today `_create_print_job_for_lines`, customer-pickup, voucher network jobs, and payment-receipt PrintJobs call `build_escpos_*` / `build_voucher_slip_text` / `build_payment_receipt_text` before insert. Those builders call `write_logo_from_event` → `_prepare_receipt_logo` (Pillow open, LANCZOS resize, `point(lambda …)`). The print worker only base64-decodes `escpos_payload` and TCP-sends. Bluetooth voucher/payment paths must keep returning payloads in the HTTP response.

Constraints:
- Preserve `escpos-receipt-logo` width/placement contracts
- Single-process uvicorn on Pi; in-process cache is enough
- SQLite `print_jobs` already stores `escpos_payload` Text + `status`; extend carefully for deferred render
- Existing tests assert print job creation and ESC/POS content; deferral must keep eventual payloads equivalent

## Goals / Non-Goals

**Goals:**
- Logo prep once per (content, width) until invalidation
- Faster threshold path without visual drift vs current fixtures
- Request path enqueues print work without Pillow on network PrintJobs
- Print worker owns render-then-send for deferred jobs

**Non-Goals:**
- Changing poll interval / wake-on-insert for the print worker
- Bundle document cache (`get_bundle_dict`)
- Sync outbox / cloud client optimizations
- Moving Bluetooth response payloads off the request path
- Purging historical `print_jobs`

## Decisions

### 1. In-process logo raster cache

**Choice:** Module-level cache in `escpos_render` (or a tiny helper) keyed by `(sha256(raw_logo_bytes), max_width)` → prepared `Image` (mode `"1"`) or precomputed raster bytes suitable for `printer.image`. Invalidate entries when sync pull updates `SyncedBundle` and logo content for an event changes (simplest: clear entire logo cache on successful `pull_bundle` / `save_bundle` that rewrites `json_body`, or compare hash of logo fields).

**Alternatives considered:**
- Persist rasters in SQLite — unnecessary persistence; process restart is rare and cold prep once is fine
- Cache only base64 decode — misses the expensive resize/threshold

**Rationale:** Matches process lifetime of the Pi backend; logo rarely changes mid-event.

### 2. Vectorize (or numpy-free fast path) the threshold

**Choice:** Replace `gray.point(lambda p: …)` with a bulk operation (e.g. `Image.eval` with a bound threshold, or convert via `point` with a 256-entry table built once). Keep threshold `175` and bbox/center canvas logic unchanged so fixture bytes stay stable where possible.

**Alternatives considered:**
- Keep lambda — simple but slow on ARM for large logos
- Add numpy — heavier dependency for little gain if a LUT/`eval` suffices

### 3. Deferred PrintJob schema: render context + empty payload until rendered

**Choice:** Add nullable `render_context_json` (Text) on `print_jobs`. For deferred jobs:
- `escpos_payload` stored as empty string `""` (or a sentinel) until render
- `status` stays `queued`
- `render_context_json` holds a versioned JSON blob: `job_kind`, station/register ids, feed_lines, article snapshot keys or inline lines already used today, flags (`kitchen_partial_print`, etc.), and enough fields for the existing `build_*` functions

Print worker tick:
1. Load queued jobs
2. If `escpos_payload` empty and context present → build bytes (logo cache), write payload, then send
3. If payload already present (legacy / sync Bluetooth-adjacent enqueue that still prebuilds, cash-drawer kick with tiny payload, retries) → send as today

**Alternatives considered:**
- New status `pending_render` vs `queued` — clearer state machine but more migration and UI/status churn; empty payload under `queued` is enough if worker treats it as render-needed
- Always prebuild but in `asyncio.to_thread` after commit — improves client latency only if response returns before thread finishes; harder to reason about failures vs a durable job row

**Rationale:** Durability matches today’s “job row = unit of print work”; crash mid-render retries on next tick.

### 4. Scope of deferral vs sync build

| Path | Behavior |
|------|----------|
| Station / customer-pickup / network voucher / payment PrintJob / shift slips that enqueue PrintJob | Defer render |
| Cash-drawer kick (tiny fixed bytes, no logo) | May stay sync prebuild (cheap) or defer with context — prefer sync prebuild to avoid schema complexity for trivial payloads |
| `voucher_escpos_payloads` Bluetooth | Sync build + logo cache |
| Payment/test APIs returning `escpos_payload` in body | Sync build + logo cache |
| Emulated printer path | Same as network: worker renders then stores emulated receipt |

### 5. Render context contents

**Choice:** Snapshot what builders need from the request moment: order payload slice (lines for that station), `event_id`, currency, station/register uuid, `job_kind`, feed_lines, printer host/port (already columns), kitchen partial flags, voucher name/value/copy indices. Prefer referencing `local_order_id` + reloading `payload_json` where the order row is the source of truth; include ephemeral fields that are not on the order (e.g. kitchen excluded lines) in the context JSON.

**Rationale:** Avoids drift if later UI edits open-order lines; print should reflect what was ordered/printed at enqueue time for kitchen slips. For station slips created at order submit, order `payload_json` already matches; kitchen partial reprints should embed the partial line set in context.

### 6. Logo cache invalidation hook

**Choice:** Call `clear_receipt_logo_cache()` from `pull_bundle` after writing the new body (and from `save_bundle` only if we want stock saves to clear — stock saves do not change logos, so **pull only** is enough; optional clear on process start is automatic).

## Risks / Trade-offs

- **[Slightly longer time-to-first-byte at printer]** → Acceptable; staff latency is HTTP response, not TCP to printer. Worker already polled at 1s.
- **[Render context JSON wrong/incomplete]** → Job goes `error`; add focused tests per job_kind. Keep cash-drawer sync to reduce surface.
- **[Fixture byte drift from threshold rewrite]** → Prefer LUT that matches threshold 175 exactly; update golden tests only if necessary and document.
- **[Empty `escpos_payload` breaks readers]** → Grep/admin UIs that assume non-empty queued payloads; treat empty as “not rendered yet” in listings/emulated preview.
- **[Concurrent first-render cache stampede]** → Unlikely on single-worker Pi; optional lock around cache fill if needed.

## Migration Plan

1. Alembic migration: add `print_jobs.render_context_json` (nullable Text).
2. Deploy Pi backend: old rows have payload filled + null context → worker sends as today.
3. New enqueues write context + empty payload; worker renders.
4. Rollback: revert code; leave column in place (nullable unused). Do not remove column in a hurry.

## Open Questions

- Whether payment-receipt PrintJobs created during settle should embed a frozen payment payload in context or always reload from `PaymentReceipt` / order at render time (prefer freeze-in-context for settle-time accuracy).
- Exact `render_context_json` schema version field (`v: 1`) naming — finalize during implement alongside tests.
