## 1. Print worker wake (D)

- [ ] 1.1 Add failing tests: enqueue/retry notifies an idle worker so queued jobs start before a full multi-second poll wait; missed wake still drains within bounded idle timeout
- [ ] 1.2 Implement module-level wake (`asyncio.Event` + `notify_print_worker`) and change `print_worker_loop` wait to wake-or-timeout; honour stop
- [ ] 1.3 Call notify after durable enqueue/retry at shared PrintJob creation and retry call sites

## 2. Off-event-loop render (D)

- [ ] 2.1 Add failing test (or instrumentation): deferred `ensure_print_job_payload` / render does not hold the event loop for the duration of CPU render (e.g. `to_thread` or equivalent)
- [ ] 2.2 Implement off-loop render with no shared SQLAlchemy Session across threads; keep TCP send async on the loop
- [ ] 2.3 Confirm render/send failure paths still mark `error` / leave retryable and satisfy `pi-receipt-render-offload`

## 3. Hot-path SQLite indexes (A)

- [ ] 3.1 Add failing tests or migration assertions for indexes on `print_jobs.status`, `order_submissions(event_id, payment_status)`, `sync_outbox.status`, `kitchen_tickets(event_id, status)`
- [ ] 3.2 Add Alembic revision after `007_synced_bundle_etag` creating those indexes; align ORM `index=True` / `__table_args__`
- [ ] 3.3 Ensure `init_test_schema` / `create_all` exposes the same indexes; add schema-patch helper only if required by existing Pi drift patterns

## 4. Verification

- [ ] 4.1 Run Pi backend tests (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [ ] 4.2 Run `./scripts/lint.sh --staged` (or full) before commit
