## Why

On multi-station cash-register orders, customer Abholbelege and the kitchen monitor UI show the correct per-station pickup codes, but station kitchen slips do not: direct station prints omit the code entirely, and printing from the kitchen monitor stamps the order’s first (scalar) code instead of that station’s code. Staff and guests then mismatch slips to Abholcodes.

## What Changes

- Stamp the per-station `pickup_code` into the station/kitchen PrintJob render payload (same as customer Abholbeleg already does), so ESC/POS heroes use the station code.
- Cover with Pi backend tests: direct `station_order` print at create, and kitchen-monitor print when the kitchen station is not the first allocated code.
- No API or UI contract changes; kitchen list/display already resolves correctly.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `station-scoped-pickups`: Clarify that station/kitchen **print job** render payloads MUST carry the station-scoped pickup code (not the order-level first code, and not omit it when the code is passed at job creation).

## Impact

- **Pi backend**: `pi/backend/app/routers/edge_common.py` (`_create_print_job_for_lines`); tests under `pi/backend/tests/test_station_scoped_pickups.py` (and/or kitchen print tests).
- **Print worker / render**: unchanged once render context payload includes the correct `pickup_code`.
- **Pi frontend / cloud**: no changes expected.
- **Ops**: after deploy, multi-station register orders print matching codes on station slips and kitchen reprints.
