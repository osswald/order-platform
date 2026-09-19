## 1. Tests first (ghost keep + item cascade)

- [x] 1.1 Add failing test: local open order with pending outbox, absent from cloud `open_orders`, survives `restore_operational_snapshot` / ghost cleanup and remains `payment_status=open`
- [x] 1.2 Add failing test: same for waiter/table-shaped open order (table_number > 0)
- [x] 1.3 Add failing test: true ghost (open, no pending/error outbox, not in cloud keep-set) is still purged
- [x] 1.4 Add failing test: when a ghost submission is purged, its `order_items` rows are deleted

## 2. Ghost cleanup keep-set + cascade

- [x] 2.1 Before `_ghost_cleanup_orders`, union keep-set with local open `client_order_id`s that have pending/error outbox for the event (bulk-friendly; reuse existing outbox helper logic)
- [x] 2.2 In `_ghost_cleanup_orders`, delete `order_items` for the submission being removed
- [x] 2.3 Run `pi/backend` operational restore tests until 1.x pass

## 3. Tests first (push before restore)

- [x] 3.1 Add failing sync-cycle test (or focused unit around `pull_and_restore` / cycle orchestration): when restore will apply on a 200 snapshot, pending submission outbox is pushed before `restore_operational_snapshot`
- [x] 3.2 Assert snapshot 304 still skips restore and does not require the pre-restore push path

## 4. Sync cycle ordering

- [x] 4.1 Implement push-of-pending-submissions (or full outbox push) before restore application when restore will run, using the cycle’s shared HTTP client
- [x] 4.2 Keep end-of-cycle push behavior coherent (no double-ack bugs; remaining non-submission entities still push)
- [x] 4.3 Run sync + restore related `pi/backend` tests until green

## 5. Verify

- [x] 5.1 Run full `pi/backend` pytest suite
- [x] 5.2 Run `./scripts/lint.sh` for touched Pi backend areas
- [x] 5.3 `npx openspec validate fix-pi-restore-ghost-purge-open-orders --strict` (or project-equivalent)
