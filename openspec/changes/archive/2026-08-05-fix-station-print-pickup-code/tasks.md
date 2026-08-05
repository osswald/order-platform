## 1. Failing tests

- [x] 1.1 Add Pi backend test: multi-station register order with direct-print station creates a `station_order` PrintJob whose rendered ESC/POS includes that station’s pickup code
- [x] 1.2 Add Pi backend test: multi-station order where the kitchen-monitor station is the second allocated code; after kitchen print, the `kitchen_ticket` PrintJob render/ESC/POS uses that station’s code (not the order scalar first code)
- [x] 1.3 Confirm both new tests fail on current code (missing/wrong stamp)

## 2. Fix stamp

- [x] 2.1 In `_create_print_job_for_lines`, when `pickup_code is not None`, set `station_payload["pickup_code"]` before building render context (mirror customer pickup)
- [x] 2.2 Re-run the new tests and existing `test_station_scoped_pickups` / kitchen print coverage; all must pass

## 3. Verify

- [x] 3.1 Run Pi backend test suite (`cd pi/backend && uv run python -m pytest tests/ -v`)
- [x] 3.2 Run lint for touched areas (`./scripts/lint.sh --staged` or full as appropriate)
