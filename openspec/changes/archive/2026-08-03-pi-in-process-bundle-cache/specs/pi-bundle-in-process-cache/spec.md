## Purpose

Keeps the organisation catalogue/config bundle in Pi process memory so edge requests reuse a parsed dict instead of re-reading and re-parsing SQLite on every call, while staying fresh after real bundle body changes.

## ADDED Requirements

### Requirement: Bundle reads reuse process memory after a successful load

After the Pi has loaded a valid organisation bundle from durable storage into process memory, subsequent reads of that bundle within the same process MUST NOT re-parse the stored JSON body from SQLite unless the in-memory copy has been invalidated or replaced. The public read helpers used by edge routes MUST continue to return a dict that is equivalent to the current durable bundle (same organisation and event catalogue/config content the caller would have received from a fresh load).

#### Scenario: Second read within a process skips SQLite JSON parse

- **WHEN** a valid organisation bundle has already been loaded into process memory
- **AND** no invalidating write has occurred since that load
- **AND** an edge request asks for the organisation bundle again
- **THEN** the response content MUST match the durable bundle
- **AND** the Pi MUST NOT perform another `json.loads` of `SyncedBundle.json_body` for that read

#### Scenario: Cold start loads from durable storage

- **WHEN** the process has no in-memory organisation bundle yet
- **AND** a valid `SyncedBundle` row exists
- **THEN** the first read MUST load and parse from durable storage
- **AND** MUST populate process memory for later reads

#### Scenario: Missing bundle still fails as today

- **WHEN** no valid organisation bundle is available in durable storage
- **AND** process memory is empty
- **THEN** reads that require a bundle MUST fail with the same client-visible error semantics as today (no silent empty catalogue)

### Requirement: Cache stays coherent with durable bundle mutations

Whenever the durable organisation bundle body is replaced with new content (including stock updates that rewrite `SyncedBundle`, a sync pull that applies a changed body, or restore logic that rewrites the bundle), the Pi MUST update or invalidate process memory so the next read reflects the new body. No-op sync pulls that leave the durable body unchanged (HTTP 304 or identical-body skip) MUST NOT force a needless cache thrash that clears unrelated caches solely because a pull ran.

#### Scenario: Stock save updates what later reads see

- **WHEN** an order path applies stock and persists an updated organisation bundle
- **AND** a later request in the same process reads the bundle
- **THEN** that read MUST observe the stock-updated article/ingredient sellable state

#### Scenario: Sync pull with new body refreshes memory

- **WHEN** a sync pull persists a changed organisation bundle body
- **THEN** subsequent in-process reads MUST observe the new body (not a stale pre-pull copy)

#### Scenario: Unchanged sync pull leaves warm cache usable

- **WHEN** a sync pull determines the organisation bundle body is unchanged (304 or local identical-body skip)
- **THEN** process memory MAY remain warm for subsequent reads
- **AND** the Pi MUST NOT treat that pull as a durable body change for bundle-cache invalidation purposes

### Requirement: Callers keep the existing read API behaviour

Edge and worker code paths that obtain the organisation bundle through the existing bundle helper entry points MUST keep working without requiring per-route API changes. Helpers that currently raise when no bundle is configured MUST continue to raise; helpers that return `None` when absent MUST continue to return `None`.

#### Scenario: get_bundle_dict still raises when unpaired

- **WHEN** the Pi has no valid synced organisation bundle
- **AND** a caller uses the strict bundle helper
- **THEN** the call MUST fail with the existing “no bundle / pull first” style error

#### Scenario: get_bundle_dict_raw still returns None when empty

- **WHEN** the Pi has no synced bundle row or empty body
- **AND** a caller uses the raw/optional helper
- **THEN** the result MUST be `None` (not an empty synthetic organisation)
