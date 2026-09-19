## Context

See proposal.md for motivation. Today `run_sync_cycle` pulls (and may restore) before pushing the outbox. `restore_operational_snapshot` builds `keep_cids` only from cloud `open_orders` (plus skip-restore ids that already appear in that list). `_ghost_cleanup_orders` then deletes every other local `open` submission. `_should_skip_order_restore` already treats pending/error outbox as “local wins” for overwrite, but that guard never runs for ids absent from the cloud list — so brand-new Fertig orders are deleted while the cashier is still on Bezahlen. Normalized `order_items` are written at create and not deleted on ghost purge, leaving OPEN orphans.

Prior change `fix-operational-restore-resurrection` explicitly deferred this ghost-cleanup hole.

## Goals / Non-Goals

**Goals:**

- Make Fertig → payment-type → settle reliable while sync is running.
- Keep true appliance-takeover / stale-open cleanup working for opens with no local outbox protection.
- Avoid leaving `order_items` pointing at purged submissions.

**Non-Goals:**

- Reworking settlement APIs or frontend pay UX.
- Healing historical orphan OPEN `order_items` on already-deployed event DBs (optional one-shot later).
- Marking `order_items` paid on successful settle (related consistency; separate follow-up if needed).
- Changing cloud snapshot schema.

## Decisions

### 1. Expand keep-set before ghost cleanup (primary)

**Choice:** Before `_ghost_cleanup_orders`, add every local open `client_order_id` for the event that has a pending/error outbox submission payload with that id (reuse `_has_pending_outbox_for_order` or a bulk scan once per event).

**Why:** Matches existing “pending outbox protects local” intent and fixes the missing-from-cloud case without requiring cloud to already know the order.

**Alternatives:**

- *Only push-before-restore* — reduces races but still loses the order if push fails or cloud snapshot lag remains within the same cycle.
- *Never ghost-delete any local open* — retains forever-stale opens after device swaps; too broad.

### 2. Push submissions before restore application (defense in depth)

**Choice:** When `needs_operational_restore` is true after a 200 snapshot, call `push_outbox` (or a submission-filtered push) on the shared client, then run `restore_operational_snapshot`. Keep a final push at end of cycle for remaining rows / non-submission entities as today if needed.

**Why:** Gives cloud a chance to include the new open before the next snapshot; pairs with keep-set so a slow/failed push still does not delete local opens.

**Alternatives:**

- *Reorder entire cycle to push-then-pull* — larger behavior change for bundle/stock; unnecessary if we only gate restore.

### 3. Cascade delete `order_items` on true ghost purge

**Choice:** In `_ghost_cleanup_orders`, delete `OrderItem` rows with `submission_id == row.id` (and/or `session` scoped if required) before deleting the submission.

**Why:** Stops OPEN-item / empty-open-session confusion after legitimate purges.

## Risks / Trade-offs

- **[Risk] Stale local open with stuck `error` outbox never purged** → **Mitigation:** Acceptable vs money-path loss; ops can clear error outbox or settle/cancel locally. Document in tasks.
- **[Risk] Push-before-restore lengthens restore-check cycles** → **Mitigation:** Only when restore will apply; idle 304 path unchanged.
- **[Risk] Cloud rejects push then restore still runs** → **Mitigation:** Keep-set from pending/error outbox still retains the order.
- **[Trade-off] Historical orphans not auto-healed** → Optional cleanup script/task later; not required for durable fix.

## Migration Plan

1. Land via PR; Pi image OTA / compose pull on appliances.
2. No schema migration required for the keep-set / sync-order fix; item cascade is runtime delete only.
3. Rollback: revert image; worst case returns to current race (known).

## Open Questions

- None blocking implementation.
