## 1. Cloud persistence and API

- [x] 1.1 Write failing cloud backend tests: edge auth with `X-Edge-App-Version` / optional build-time headers persists on credential; omit/empty leaves prior values; appliance detail exposes fields
- [x] 1.2 Add Alembic migration + model columns `reported_app_version`, `reported_app_build_time` on `appliance_edge_credentials`
- [x] 1.3 Update edge auth to read/validate headers and stamp credential alongside `last_seen_at`
- [x] 1.4 Extend `ApplianceEdgeCredentialRead` and appliance mapping; regenerate OpenAPI + cloud frontend types
- [x] 1.5 Run cloud backend tests until green

## 2. Pi reporting

- [x] 2.1 Write failing Pi tests that authenticated `cloud_client` requests include version headers from `version_info`
- [x] 2.2 Add version headers in `cloud_client._headers` (and any other edge auth header builders)
- [x] 2.3 Run Pi backend tests until green

## 3. Cloud Appliances UI

- [x] 3.1 Write failing frontend test(s) for SD-card table Version column (reported value vs empty)
- [x] 3.2 Add Version column + i18n (de/en); format `v{version}` with optional build time
- [ ] 3.3 Run cloud frontend tests / typecheck for touched areas

## 4. Verify

- [ ] 4.1 Run `./scripts/lint.sh` (or `--staged`) on changed areas
- [ ] 4.2 Confirm no `VERSION` bump in the feature PR
