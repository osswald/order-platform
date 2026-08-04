## MODIFIED Requirements

### Requirement: Cache stays coherent with durable bundle mutations

Whenever the durable organisation catalogue body is replaced with new content (a sync pull that applies a changed body, or restore logic that rewrites the catalogue), or whenever local monitored stock is persisted (including via the local stock overlay path that does not rewrite `SyncedBundle.json_body`), the Pi MUST update or invalidate process memory so the next read reflects the new effective body. No-op sync pulls that leave the durable catalogue body unchanged (HTTP 304 or identical-body skip) MUST NOT force a needless cache thrash that clears unrelated caches solely because a pull ran, and MUST NOT require a stock re-persist to keep the cache coherent.

#### Scenario: Stock save updates what later reads see

- **WHEN** an order path applies stock and persists local stock state (catalogue rewrite or overlay)
- **AND** a later request in the same process reads the bundle
- **THEN** that read MUST observe the stock-updated article/ingredient sellable state

#### Scenario: Sync pull with new body refreshes memory

- **WHEN** a sync pull persists a changed organisation catalogue body
- **THEN** subsequent in-process reads MUST observe the new effective body (not a stale pre-pull copy), including any rebuilt local stock overrides required after that pull

#### Scenario: Unchanged sync pull leaves warm cache usable

- **WHEN** a sync pull determines the organisation catalogue body is unchanged (304 or local identical-body skip)
- **THEN** process memory MAY remain warm for subsequent reads
- **AND** the Pi MUST NOT treat that pull as a durable catalogue body change for bundle-cache invalidation purposes
- **AND** effective stock already present in process memory MUST remain correct without a reapply-driven rewrite
