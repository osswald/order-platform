## 1. Cloud backend

- [x] 1.1 Add failing tests for `bluetooth_printing_enabled` default, event response, and edge bundle
- [x] 1.2 Add Event column, schema patch, Pydantic schemas, CRUD/helpers, event_copy, EdgeEventBundle

## 2. Cloud frontend

- [x] 2.1 Add Stammdaten switch + form/Events.vue wiring + de i18n
- [x] 2.2 Export OpenAPI and regenerate cloud frontend API types

## 3. Pi frontend

- [x] 3.1 Add helper + tests; gate payment receipt, voucher, and shift Bluetooth paths
- [x] 3.2 Gate WaiterHub Bluetooth tile when event flag is off; update tests

## 4. Verify

- [x] 4.1 Run affected cloud backend and Pi frontend tests; run lint on staged changes
