## 1. Logo cache and fast prepare

- [x] 1.1 Add failing tests for logo cache reuse (same bytes+width → identical raster; different width → distinct; clear on invalidation) and for threshold path matching current visual contract (`test_escpos_render` / paper-width fixtures)
- [x] 1.2 Implement in-process logo cache + `clear_receipt_logo_cache()`; switch `_prepare_receipt_logo` / `write_logo_bytes` to use it
- [x] 1.3 Replace per-pixel `point(lambda …)` with a LUT / bulk threshold (keep cutoff 175 and canvas/bbox behavior)
- [x] 1.4 Hook cache clear on successful bundle pull (`pull_bundle`); confirm stock-only `save_bundle` does not need clear

## 2. Deferred PrintJob schema

- [x] 2.1 Add failing tests: order create enqueues station/customer-pickup jobs with empty `escpos_payload` + non-empty render context; worker later fills payload and marks `sent` (or `error`)
- [x] 2.2 Alembic migration + ORM: nullable `print_jobs.render_context_json`; keep `escpos_payload` non-null (use `""` until rendered)
- [x] 2.3 Define versioned render-context JSON (`v: 1`) covering station, customer-pickup, network voucher, and payment-receipt PrintJobs (freeze settle-time payment fields in context)

## 3. Enqueue path offloads render

- [x] 3.1 Change `_create_print_job_for_lines` / customer-pickup / network voucher PrintJob helpers to write context + empty payload (no `build_escpos_*` on request path)
- [x] 3.2 Defer payment-receipt PrintJob builders the same way; keep cash-drawer kicks as sync prebuilt payloads (no logo)
- [x] 3.3 Keep Bluetooth `voucher_escpos_payloads` and payload-returning payment/test APIs synchronous; ensure they use the logo cache
- [x] 3.4 Update any listing/preview code that assumes queued jobs always have non-empty ESC/POS

## 4. Print worker render-then-send

- [x] 4.1 In `process_print_job` / worker loop: if payload empty and context present, build ESC/POS (shared builders + logo cache), persist payload, then send; on failure set `error` + `last_error`
- [x] 4.2 Preserve legacy behavior for pre-filled payloads (null context)
- [x] 4.3 Add/adjust tests for render failure, emulated printer path, and multi-job order create (logo prepared once across jobs in-process)

## 5. Verification

- [x] 5.1 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [ ] 5.2 Run `./scripts/lint.sh --staged` (or full) before commit
