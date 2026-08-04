## Purpose

Keeps the Pi FastAPI event loop responsive during print bursts and cuts idle print-worker churn by waking on enqueue and building deferred ESC/POS payloads off the event loop.

## ADDED Requirements

### Requirement: Print worker wakes promptly when work is queued

When a network `PrintJob` becomes `queued` (new enqueue or retry), the Pi print worker SHALL begin processing without waiting for a full idle poll interval whenever the process is running. The worker MAY still use a bounded idle timeout as a safety net so orphaned queued rows are eventually claimed after missed wakes or restarts.

#### Scenario: Enqueue wakes an idle worker

- **WHEN** the print worker is idle waiting for work
- **AND** a new `PrintJob` is committed with `status = queued`
- **THEN** the worker MUST start a processing pass for queued jobs sooner than the previous fixed one-second-only poll would guarantee

#### Scenario: Retry wakes the worker

- **WHEN** an existing print job is set back to `queued` via retry
- **THEN** the worker MUST be eligible to process that job without relying solely on the next periodic poll tick

#### Scenario: Queued rows survive missed wakes

- **WHEN** a wake signal is missed or the process restarts with durable `queued` rows
- **THEN** the worker MUST still claim and process those rows within a bounded idle interval

### Requirement: Deferred ESC/POS render does not block the event loop

Building the ESC/POS payload for a deferred network `PrintJob` (from persisted render context) MUST NOT block the FastAPI asyncio event loop. CPU-heavy render work SHALL run off the event loop (for example in a worker thread). Asynchronous printer TCP send MAY remain on the event loop. Until render succeeds, the job MUST remain eligible for processing (not marked `sent`), consistent with `pi-receipt-render-offload`.

#### Scenario: Render during concurrent HTTP

- **WHEN** the print worker is rendering a deferred job’s ESC/POS payload
- **AND** another request arrives on the same Pi backend process
- **THEN** that request MUST NOT be blocked waiting for the render CPU work to finish on the event loop

#### Scenario: Render failure stays retryable

- **WHEN** off-loop render fails for a deferred job
- **THEN** the job MUST NOT be marked `sent`
- **AND** MUST remain processable or recorded as `error` with `last_error` as today

### Requirement: Shutdown and batching behaviour remain safe

The print worker SHALL continue to respect process shutdown and SHALL process durable queued jobs in bounded batches. Wake-on-enqueue MUST NOT skip the durable queue or require in-memory-only job delivery.

#### Scenario: Stop still interrupts idle wait

- **WHEN** the print worker is waiting idle for work or timeout
- **AND** the process requests print-worker stop
- **THEN** the idle wait MUST end and the worker loop MUST exit cleanly
