## 1. Catalog sync (backend)

- [x] 1.1 Add failing tests: list imports a remote reader (label from `name`), preserves existing local label, prunes ids missing from well-formed `items`, does not prune when SumUp errors or `items` is missing/not a list, empty `items` prunes all, prune clears matching cash-register `sumup_reader_id`
- [x] 1.2 Make `list_readers` distinguish well-formed `{items: [...]}` from malformed payloads (do not treat missing `items` as empty catalog)
- [x] 1.3 Add nullable `device_identifier` / `device_model` on `SumupReader` (model + `database.py` patch; Alembic revision if required by cloud migrations)
- [x] 1.4 Replace status-only list sync with catalog upsert (insert with name/serial/`Solo` label, refresh status + device fields, prune + clear register bindings)
- [x] 1.5 Return serial/model on the readers list API
- [x] 1.6 Run cloud backend reader tests

## 2. Import on connect

- [x] 2.1 Add failing connect/update tests: successful connect imports merchant readers; same-merchant key update re-syncs; connect still succeeds when list_readers fails (local rows unchanged)
- [x] 2.2 Call the catalog-sync helper after successful API-key connect and same-merchant update (best-effort; do not roll back credentials)
- [x] 2.3 Run cloud backend connect tests

## 3. Telemetry endpoint

- [x] 3.1 Add failing tests for `GET …/readers/{id}/telemetry`: maps SumUp `/status` plus stored serial/model; 404 for unknown local reader; SumUp failure returns identity + telemetry unavailable without dropping the reader
- [x] 3.2 Add `get_reader_status` in `sumup_client` and the telemetry route (org-admin ACL, connected org required)
- [x] 3.3 Export OpenAPI and regenerate cloud frontend API types
- [x] 3.4 Run cloud backend reader/telemetry tests

## 4. SumUp-Geräte tooltip

- [x] 4.1 Add failing frontend tests for telemetry fetch helper and tooltip rendering (live fields vs degraded copy)
- [x] 4.2 Fetch telemetry on hover (`v-tooltip` on reader label); show serial/model, online/offline, battery, connection, firmware, last activity
- [x] 4.3 Add de/en i18n for tooltip and telemetry-unavailable
- [x] 4.4 Run cloud frontend tests and typecheck for touched files

## 5. Docs and verification

- [x] 5.1 Update `docs/sumup-cloud-api.md`: connect imports catalog; list re-syncs; prune when absent from SumUp; tooltip telemetry
- [x] 5.2 Run targeted cloud backend + frontend SumUp tests and `./scripts/lint.sh` for touched areas
