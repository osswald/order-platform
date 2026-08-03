## Context

See proposal.md for motivation. Today every stocked order calls `apply_stock_to_bundle` then `save_bundle`, which `json.dumps`s the full organisation dict into `SyncedBundle.json_body` (including receipt logos). `pull_and_restore` always calls `reapply_pending_stock` after `pull_bundle`; on 304 / identical-body the returned dict is already the locally deducted bundle, so reapply subtracts pending lines again and `save_bundle`s. In-process cache (`pi-bundle-in-process-cache`) already stays warm across no-op pulls and refreshes on `save_bundle`. SQLite is `WAL` + `synchronous=NORMAL`; Alembic head is `008_hot_path_indexes`.

## Goals / Non-Goals

**Goals:**
- Order/stock paths persist only small stock rows (or equivalent), not the full catalogue TEXT blob
- Effective bundle reads (helpers + cache) keep showing correct `in_stock` / `sellable` after local deductions
- Reapply pending outbox stock only onto a fresh cloud catalogue baseline; never on 304 / identical skip
- One Alembic migration + ORM alignment; tests cover order stock, reapply-after-pull, and no-op pull

**Non-Goals:**
- Changing cloud stock APIs or outbox payload shape
- Splitting logos into a separate blob store (overlay is enough to stop rewriting them on stock)
- Chunked bundle download; register-display / print retention work
- Guaranteeing zero double-apply for every historical edge case beyond pending/error outbox + pull semantics

## Decisions

### 1. Absolute local stock overlay table (not delta-only, not dual JSON blobs)

**Choice:** Add a durable SQLite table (name e.g. `local_stock_state`) keyed by `(event_id, entity_kind, entity_id)` storing absolute local `in_stock` (and enough fields to rebuild sellable / monitor flags consistently with `stock.py` snapshots). Entity kinds cover monitored **articles** and **ingredients**.

**Effective bundle:** Cold `get_bundle_dict*` loads `SyncedBundle.json_body`, merges overlay values onto matching event article/ingredient entries (overlay wins for keys present), then caches the **effective** dict. Warm cache continues to serve effective stock.

**Stock mutation path:** `apply_stock_to_bundle` stays the in-memory mutator. Persistence becomes upsert overlay rows for changed entities + `set_bundle_cache(effective)` — **do not** rewrite `SyncedBundle.json_body` for ordinary stock updates.

**Catalogue writes:** Real sync pull body change and restore paths that replace the organisation catalogue continue to write `SyncedBundle.json_body` (as today). On those writes: **clear overlay**, then if pending/error outbox exists, reapply onto the new baseline and upsert overlay from the result (or skip overlay writes when outbox empty so cloud stock shows through).

**Alternatives considered:**
- *Delta overlay (pending deductions only):* every read must scan outbox or maintain deltas carefully; harder with composite/ingredient rules already in `apply_stock_to_bundle`.
- *Strip logos into a second TEXT column only:* still rewrites large catalogue JSON on stock; less SD win.
- *Keep rewriting SyncedBundle but gzip / omit logos on stock save:* fragile fingerprint/ETag interaction; logos still need to round-trip on pull.

### 2. Gate reapply on `bundle_changed` (G)

**Choice:** `pull_and_restore` calls `reapply_pending_stock` only when `pull_result["bundle_changed"]` is true (real new catalogue body persisted). On 304 / identical-body skip: **do not** reapply and **do not** persist stock. After operational restore that mutates the in-memory/catalogue bundle baseline, keep an explicit reapply (as today when restore applies).

**No-op persistence:** Even when reapply runs, skip durable writes if no stock fields changed (empty pending lines / no monitored entities touched).

**Why:** Local order path already deducted stock before outbox ack. Reapply exists to re-stamp cloud baselines that lack those deductions — not to re-process an already-local effective bundle.

### 3. Keep `save_bundle` as a chokepoint with two modes (or split helpers)

**Choice:** Evolve `save_bundle` (or split into `persist_catalogue_bundle` + `persist_local_stock`) so call sites stay few: order create, reapply, restore. Catalogue mode writes `json_body` + cache + collective-bill ensure; stock mode writes overlay + cache only. Grep for `SyncedBundle.json_body =` remains the audit path.

**`ensure_instant_collective_bills_for_bundle`:** run on catalogue persists; not required on pure stock overlay upserts.

### 4. Migration / empty overlay compatibility

**Choice:** Fresh overlay table starts empty. Existing appliances whose `json_body` already embeds local deductions continue to work (merge is no-op). First real cloud body change after upgrade clears overlay and reapplies pending — the correct long-term state. No one-shot backfill required.

### 5. Tests first

**Choice:** Failing tests before implementation:
- Order stock path does not change `SyncedBundle.json_body` (or `updated_at`) while sellable updates for later reads
- `reapply_pending_stock` after a cloud baseline yields correct counts (existing `test_sync_stock` intent)
- `pull_and_restore` on 304 with pending outbox does not rewrite catalogue and does not double-decrement effective stock
- Cold load after restart merges overlay into effective reads

## Risks / Trade-offs

- **[Stale overlay after catalogue pull if clear/reapply forgotten]** → Single chokepoint on catalogue persist; tests for pull+pending and pull+empty outbox
- **[Double source of truth confusion]** → Document: `json_body` = last cloud (or restored) catalogue baseline; overlay = local absolute stock overrides; effective = merge
- **[Fingerprint / restore using catalogue vs effective]** → Operational restore and content fingerprints that intentionally ignore ephemeral stock must keep using the same rules as today; do not feed overlay into cloud ETag body
- **[Composite sellable recompute]** → Continue to run `_recompute_composite_sellable` on the in-memory effective event after apply/merge so UI sellable matches today
- **[Slightly more complex reads]** → Accept merge cost on cold start; warm path unchanged (cached effective)

## Migration Plan

1. Alembic `009_*` after `008_hot_path_indexes` creating overlay table + indexes `(event_id, entity_kind, entity_id)` unique
2. Ship Pi backend with merge + gated reapply
3. Rollback: revert code; overlay table can remain unused (harmless) or drop in down revision

## Open Questions

None that block specs or tasks — table/column naming and whether `save_bundle` splits into two functions are implementer details.
