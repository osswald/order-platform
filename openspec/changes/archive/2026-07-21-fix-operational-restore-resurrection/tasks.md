## 1. Regression tests (write first)

- [x] 1.1 Add test: local all-done kitchen tickets + empty cloud kitchen → restore leaves tickets done and list-empty for that order
- [x] 1.2 Add test: local all-done kitchen tickets + stale open/partial cloud kitchen → restore does not apply cloud tickets
- [x] 1.3 Add test: cloud open order with no kitchen tickets on empty local → restore creates order but no kitchen tickets (no line regen)
- [x] 1.4 Add test: cloud open order with kitchen tickets on empty local → restore still applies cloud tickets (takeover path)
- [x] 1.5 Add test: local `paid` order + cloud open payload → restore does not reopen order or rewrite kitchen
- [x] 1.6 Add test: local open order with pending outbox for `client_order_id` → restore does not overwrite local payload
- [x] 1.7 Add test: local open order with fewer sellable line qtys than cloud → restore keeps reduced local lines

## 2. Kitchen restore guards

- [x] 2.1 Implement “local all-done ⇒ skip kitchen rewrite” in `_restore_kitchen_tickets` (or caller)
- [x] 2.2 Remove regenerate-from-lines fallback when cloud tickets are empty/missing
- [x] 2.3 Keep apply-from-cloud path when cloud tickets are non-empty and local is not all-done

## 3. Order restore guards

- [x] 3.1 Skip restoring an order when local row is `payment_status = paid`
- [x] 3.2 Skip overwriting local open order when pending/error outbox exists for that `client_order_id`
- [x] 3.3 Skip overwriting local open order when local remaining sellable qtys are strictly behind cloud (fewer than cloud)
- [x] 3.4 Ensure skipped orders do not receive kitchen restore in the same cycle

## 4. Verification

- [x] 4.1 Run `cd pi/backend && uv run python -m pytest tests/test_operational_restore.py tests/test_kitchen_monitor.py -v`
- [x] 4.2 Run full Pi backend test suite `uv run python -m pytest tests/ -v`
- [x] 4.3 Run `./scripts/lint.sh --staged` (or full lint) before commit
