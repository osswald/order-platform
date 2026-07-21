## Context

Pi sync cycles pull a cloud operational snapshot and, when local vs cloud fingerprints differ, call `restore_operational_snapshot` **before** pushing the outbox. Restore rewrites open orders from the cloud mirror and, for each restored order, rewrites kitchen tickets via `_restore_kitchen_tickets`.

Today that helper:

1. Deletes all local kitchen tickets for the order.
2. If cloud sent tickets → recreates them.
3. If cloud sent none → **regenerates brand-new `open` tickets from order lines** (for printers in kitchen monitors).

Cloud deletes the kitchen mirror row when all tickets are `done`, while the order mirror can linger as `open` until a paid submission is acked. That combination + pull-before-push produces resurrection: finished kitchen work and settled/partially settled tables come back after unrelated local activity (e.g. new orders) triggers restore.

## Goals / Non-Goals

**Goals:**

- Finished kitchen work on a live Pi must not reappear on the kitchen monitor after restore.
- Locally paid orders must not be reopened from a stale cloud open snapshot.
- Locally progressed open orders (partial settle reduced lines, pending outbox) must not be overwritten by older cloud payloads.
- Empty-Pi / takeover restore of genuine open cloud state (orders + kitchen tickets) must keep working.
- Behavior covered by automated Pi backend tests.

**Non-Goals:**

- Changing sync cycle order (push-before-pull) — useful follow-up, not required to fix resurrection.
- Cloud mirror schema or edge API changes.
- Kitchen monitor UI, polling, or list filters (age TTL, etc.).
- Multi-writer / two-Pi concurrent selling (already unsupported).
- Deleting historical `done` kitchen rows from SQLite.

## Decisions

### 1. Kitchen restore decision tree (local completion wins)

**Decision:** Replace unconditional delete+apply/regen with:

```
if local has kitchen tickets AND all status == "done":
    skip kitchen rewrite (keep local rows)
elif cloud provided non-empty tickets:
    replace local tickets from cloud (current apply path)
else:
    do nothing (no regenerate-from-lines fallback)
```

**Why:** Same-Pi resurrection happens when cloud kitchen is empty (done already mirrored) or stale, while local already finished. Skipping all-done and removing empty-cloud regen closes both paths.

**Alternatives considered:**

- *Only skip when local all-done; keep regen for empty cloud* — still resurrects after local done rows were deleted (ghost cleanup) or on takeover after kitchen finished but table unpaid.
- *Push before restore* alone — reduces races but does not fix empty-kitchen regen against lingering open order mirrors.

### 2. Order restore: do not reopen local paid

**Decision:** When a local `LocalOrder` exists with `payment_status == "paid"` for the same `client_order_id`, skip restoring that order from a cloud open payload (leave local paid row and its kitchen state alone). Do not add it to kitchen restore for that cycle.

**Why:** Confirmed incident included a table reappearing unpaid/partial after restore; `_restore_order` currently overwrites `payment_status` from cloud.

**Alternatives considered:**

- *Always prefer cloud for takeover* — wrong on a live Pi where payment already succeeded locally and paid push is merely delayed/failed.
- *Compare timestamps only* — payloads lack a reliable shared “settled_at vs mirror updated_at” contract across all paths; paid flag is the durable local signal.

### 3. Order restore: protect progressed open locals

**Decision:** If local order is `open` and either:

- there is a pending/error outbox `submission` (or coalesced order payload) for that `client_order_id`, or
- local open lines are a strict subset / fewer sellable qty than cloud open lines (partial settle progressed locally),

then do **not** overwrite local `payload_json` / payment fields from cloud for that order. Still allow restore of *other* orders in the snapshot.

**Why:** Partial settle shrinks lines and syncs asynchronously; restore currently replaces with the older full line set, undoing partial payment appearance and feeding kitchen regen with paid items.

**Alternatives considered:**

- *Fingerprint-only skip of entire event restore* — too coarse; would block legitimate restore of other tables.
- *Merge line quantities* — complex and error-prone vs “local ahead ⇒ skip order”.

### 4. Takeover / empty local remains cloud-driven

**Decision:** If no local order row exists for a cloud open `client_order_id`, restore the order as today. Kitchen: apply cloud tickets if present; if absent, leave with **no** kitchen tickets (no regen). New local orders after takeover create tickets via the normal order path.

**Why:** Cloud kitchen absence after done means “kitchen finished,” not “rebuild.” Inventing tickets on blank Pi for unpaid leftover tables was the same semantic bug as live resurrection.

**Trade-off:** Rare case where kitchen never mirrored (very old builds / monitors enabled later) won’t get tickets back on takeover until staff re-order or we add an explicit operator action (out of scope).

### 5. Scope of code changes

**Decision:** Implement guards inside `pi/backend/app/operational_restore.py` (`_restore_order` callers / `_restore_kitchen_tickets` / small helpers). Keep `run_sync_cycle` pull-then-push order unchanged in this change. Extend `test_operational_restore.py` with resurrection regression cases.

## Risks / Trade-offs

- **[Risk] Takeover of unpaid table with finished kitchen shows no kitchen tickets** → **Mitigation:** Accepted; matches “absence = done.” Staff can re-fire via new order if needed later.
- **[Risk] Skipping restore while outbox pending leaves local divergent from cloud open set** → **Mitigation:** Next successful push updates cloud; subsequent cycle fingerprints should converge. Document that pending outbox means local is source of truth for that order.
- **[Risk] Ghost cleanup still deletes unsynced local open orders not in cloud keep-set** → **Mitigation:** Out of scope for this change but noted; separate hardening if new orders vanish during restore. Guards here focus on not resurrecting finished/settled state.
- **[Risk] Fingerprint still triggers frequent restore** → **Mitigation:** Acceptable if restore becomes a no-op for protected orders; optional later: exclude protected locals from mismatch pressure / push-first.

## Migration Plan

- Deploy Pi backend with the new restore guards (no DB migration).
- No cloud deploy required.
- Rollback: revert Pi backend; worst case returns to previous resurrection behavior.
- No data backfill.

## Open Questions

- None blocking implementation; push-before-pull and ghost-cleanup of unsynced opens are follow-ups if still needed after this fix.
