## 1. Cloud schema and API

- [x] 1.1 Add `events.pickup_prefix_mode` (default `register`) and nullable `event_stations.pickup_code_prefix`; verify migration applies cleanly on a fresh and existing DB
- [x] 1.2 Expose mode and station prefix on event/configuration read and write schemas (OpenAPI); verify generated schema includes both fields
- [x] 1.3 Reject `pickup_prefix_mode` changes when event status is not `config` with a stable error code; verify with API tests for `config` allowed and `test`/`prod`/`archive` rejected
- [x] 1.4 When mode is `station`, validate required unique station prefixes (`^[A-Z]{1,3}$`) and that every app-layout article belongs to a station; verify invalid saves fail and valid saves succeed
- [x] 1.5 Include `pickup_prefix_mode` and station `pickup_code_prefix` in the edge bundle; verify bundle payload in cloud edge tests
- [x] 1.6 Copy `pickup_prefix_mode` and station prefixes (and existing register prefixes) on event copy; verify copy tests

## 2. Cloud frontend

- [x] 2.1 Regenerate OpenAPI client types after backend schema export; verify `pickup_prefix_mode` and station prefix appear in generated types
- [x] 2.2 Add mode control on event configuration; show register prefixes only in `register` mode and station prefixes only in `station` mode; verify UI unit/component tests for visibility
- [x] 2.3 Disable mode control when status ≠ `config` and surface lock messaging; verify component test
- [x] 2.4 Add i18n strings (de/en) for mode label, field labels, and validation/lock messages; verify keys resolve in both locales

## 3. Pi counters and allocation

- [x] 3.1 Migrate `event_pickup_counters` to support per-station rows (`station_uuid` sentinel `''` for event-wide); verify migration and model load
- [x] 3.2 Extend `_allocate_pickup_number` to accept optional `station_uuid` and advance the matching counter; verify unit tests for independent station sequences vs shared register-mode sequence
- [x] 3.3 In cash-register order creation, read `pickup_prefix_mode` from the event bundle: register mode uses register prefix + event-wide counter; station mode uses station prefix + per-station counter and fails if `station_uuid` is null; verify `test_station_scoped_pickups` (and new mode cases) pass
- [x] 3.4 Update operational restore / max-pickup rebuild for per-station counters in station mode; verify restore tests
- [x] 3.5 Ensure event lifecycle purge (including **test → prod** reconcile) deletes all pickup counter rows for the event (event-wide and per-station) so the next allocation starts at `1`; verify lifecycle tests assert counters are gone and a post-purge allocation returns `1`

## 4. Regression and lint

- [ ] 4.1 Run cloud backend tests for event config validation, copy, and edge bundle; verify suite green for touched areas
- [x] 4.2 Run Pi backend station-scoped pickup and order allocation tests; verify suite green for touched areas
- [x] 4.3 Run `./scripts/lint.sh` (or staged equivalent) on changed paths; verify lint passes
