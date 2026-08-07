## 1. Backend: basket generation and job core

- [ ] 1.1 Write unit tests for basket generation (1–8 people, station sampling, weighted preselected additions, skip unsellable/additions-empty edge cases)
- [ ] 1.2 Implement basket generator using event articles/stations/additions from the cached bundle
- [ ] 1.3 Write tests for load-test module state: single-flight, idle after stop, no persistence assumptions
- [ ] 1.4 Implement in-memory load-test job module (status dict, start/stop flags, burst scheduling ~1/min)

## 2. Backend: create → settle → receipt path

- [ ] 2.1 Write tests that a waiter actor create+cash settle uses table range and produces a settled order (reuse existing order fixtures)
- [ ] 2.2 Write tests that a register actor create+cash settle attempts cash-drawer side effect like normal settle
- [ ] 2.3 Write tests for ~30% payment-receipt print invocation (deterministic RNG seed) and skip when no print target
- [ ] 2.4 Implement actor placement: concurrent burst gather calling shared create/settle/receipt helpers
- [ ] 2.5 Write tests for hard gate: start rejected when status ≠ test; running job aborts when status leaves test
- [ ] 2.6 Wire status re-check each burst and failure counting without aborting the whole job on single order errors

## 3. Backend: HTTP API

- [ ] 3.1 Write API tests for `POST /v1/load-test/start`, `GET /v1/load-test/status`, `POST /v1/load-test/stop` (validation, 409 single-flight, 409 non-test)
- [ ] 3.2 Implement load-test router + schemas; register on the Pi FastAPI app
- [ ] 3.3 Cap waiter/register counts against event inventory; return effective config in status

## 4. Frontend: Admin Lasttest UI

- [ ] 4.1 Write tests: Lasttest tile/route gated with `isEventTest`; form shows caps from event waiters/registers
- [ ] 4.2 Add route + Betrieb tile + `AdminOperationsLoadTestView` (config fields, estimated duration, Start/Stop)
- [ ] 4.3 Implement start/stop client calls and ~1s status polling while running (placed/failed/receipts/bursts)
- [ ] 4.4 Extend `useAdminOperations` (or sibling composable) for load-test busy/progress without breaking Testdruck

## 5. Verification

- [ ] 5.1 Run Pi backend pytest for new/affected tests
- [ ] 5.2 Run Pi frontend Vitest for new/affected tests
- [ ] 5.3 Run `./scripts/lint.sh --staged` (or full) before commit
