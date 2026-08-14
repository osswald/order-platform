## 1. Pi display WebSocket

- [x] 1.1 Add failing tests for register display WS: snapshot on connect, broadcast after PUT, HTTP GET unchanged
- [x] 1.2 Implement in-process subscriber registry + `WS /v1/registers/{uuid}/display/ws` and broadcast from `put_register_display`
- [x] 1.3 Add Pi frontend display WebSocket client (subscribe, apply payload, reconnect + GET snapshot); keep slow poll only while disconnected

## 2. Customer display UX (realtime)

- [x] 2.1 Add failing tests/helpers for overflow layout stability (scrollbar gutter / grid columns)
- [x] 2.2 Fix `RegisterDisplayView` ordering layout so prices stay horizontally stable when the list scrolls
- [x] 2.3 Add failing tests for `sumup_connected` display payload from pay hooks
- [x] 2.4 Push `state: sumup_connected` when SumUp connected terminal collection starts; render waiting copy on display
- [x] 2.5 Add failing tests: Twint cancel and SumUp connected fail/abort restore ordering (cart) display
- [x] 2.6 Implement `onTwintHide` and SumUp abort path to re-push ordering payload (lines + total)
- [x] 2.7 Add failing tests for success badges + Abholbon / Abholbons copy by code count
- [x] 2.8 Update success UI: pickup codes as badges; singular/plural Abholbon(s) footer

## 3. Cloud screensaver gallery

- [x] 3.1 Add failing API tests for org gallery CRUD (max 10, size/type limits, delete; no reorder)
- [x] 3.2 Implement org screensaver image storage model + upload/list/delete endpoints
- [x] 3.3 Add edge authenticated download-by-hash endpoint scoped to credential organisation
- [x] 3.4 Include screensaver manifest (sha256, mime) in edge bundle — no image bytes; order insignificant
- [x] 3.5 Regenerate OpenAPI / cloud frontend types as needed
- [x] 3.6 Add cloud admin UI to manage org screensaver gallery (upload, delete, enforce max 10; no reorder UI)

## 4. Pi screensaver sync and lifecycle

- [x] 4.1 Add failing tests: download missing hashes once; skip existing; GC removed hashes; wipe on org change and unpair
- [x] 4.2 Implement local content-addressed screensaver store + sync after bundle pull
- [x] 4.3 Hook wipe into `reconcile_bundle_lifecycle` (org/appliance change) and `purge_on_unpair`
- [x] 4.4 Expose local HTTP serve path for stored images used by the customer display

## 5. Idle gallery on customer display

- [x] 5.1 Add failing frontend tests for idle gallery vs welcome fallback vs leaving on non-idle
- [x] 5.2 Implement idle screensaver playback from local Pi images (rotation; order unspecified); fallback `Herzlich Willkommen`

## 6. Verification

- [x] 6.1 Run Pi backend tests, Pi frontend tests, and cloud backend tests for touched areas
- [x] 6.2 Run `./scripts/lint.sh` on changed areas
