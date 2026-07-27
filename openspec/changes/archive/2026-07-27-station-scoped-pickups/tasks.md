## 1. Schema and models

- [x] 1.1 Add failing Pi backend tests for multi-station allocation, independent ready/picked-up, single-station parity, and open-orders multi-code row
- [x] 1.2 Add `station_pickups` table (Alembic / schema patch) and SQLAlchemy model with order link, station uuid, code, status, ready/picked-up timestamps
- [x] 1.3 Snapshot `pickups[]` (or equivalent) onto order payload for sync/restore; keep scalar `pickup_code` as first code

## 2. Order create and printing

- [x] 2.1 Allocate one pickup number per station group at cash-register order create; create station_pickup rows; set create response `pickup_codes` + `pickup_code`
- [x] 2.2 Stamp each customer Abholbeleg and station/kitchen print payload with that station’s code
- [x] 2.3 Mark station pickups `ready` immediately for groups without kitchen tickets; leave kitchen-backed groups `pending`

## 3. Kitchen readiness and pickup API

- [x] 3.1 On kitchen ticket → `done`, mark the matching station pickup `ready` (do not wait for siblings)
- [x] 3.2 Resolve kitchen list/print pickup code from the station pickup for that ticket’s station
- [x] 3.3 Change pickup list to return one entry per station pickup; add picked-up-by-pickup-id endpoint; apply ready TTL per station pickup
- [x] 3.4 Update OpenAPI / Pi generated types for create response, open-orders, and pickup schemas

## 4. Register and pickup UI

- [x] 4.1 Update PickupScreen to list/mark picked-up by station pickup entries
- [x] 4.2 Show all `pickup_codes` on register customer display and pay-success flows
- [x] 4.3 Open-orders hub: one row; display all codes (e.g. `A1, A2`); adjust tests

## 5. Settlement, restore, verification

- [x] 5.1 Ensure partial settle keeps all station pickups on the original open order (tests)
- [x] 5.2 Restore station pickups from order payload when recreating open register orders; shim pre-upgrade scalar-only orders if needed
- [x] 5.3 Run Pi backend + frontend tests and `./scripts/lint.sh` for touched areas
