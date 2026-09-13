## 1. Tests first

- [x] 1.1 Add/extend `EventStammdatenFields` tests: mode select present; disabled + hint when status ≠ `config`; emits/updates `pickupPrefixMode`
- [x] 1.2 Update Stationen/Kassen pickup-prefix section specs: assert mode select is absent; letter fields still show/hide by mode prop
- [x] 1.3 Add/adjust `eventDetailSave` (or Events save) coverage: Stammdaten payload includes `pickup_prefix_mode`; remove/rewrite tests for autosave mode PUT / baseline-after-mode-save if those helpers are deleted
- [x] 1.4 Add cloud backend HTTP round-trip test if missing: PUT `pickup_prefix_mode=station` then GET returns `station` (while status is `config`)

## 2. Stammdaten UI

- [x] 2.1 Add **Abholcode-Buchstabe von** select to `EventStammdatenFields` Konfiguration group (options Kasse/Station; lock + hint when status ≠ `config`)
- [x] 2.2 Wire i18n keys for Stammdaten placement if labels need `events.stammdaten.*` (reuse existing `events.config.pickupPrefixMode*` if preferred and documented)

## 3. Remove mode from Stationen / Kassen / autosave bridge

- [x] 3.1 Remove mode `v-select` from `EventConfigStationsSection` and `EventConfigCashRegistersSection`; keep mode as read-only prop for letter-field visibility
- [x] 3.2 In `EventConfiguration.vue`: stop editing mode via sections; remove mode from autosave snapshot/watch; remove second event PUT and `pickupPrefixModeSaved` emit
- [x] 3.3 In `Events.vue`: drop `onPickupPrefixModeSaved` / baseline patch wiring; pass mode into configuration only so letter fields follow form state (after Stammdaten save / load)
- [x] 3.4 Delete unused helpers (`pickupPrefixModeOnlyUpdatePayload`, `stammdatenBaselineAfterPickupPrefixModeSave`, `eventConfigurationAutosaveSnapshot` mode coupling) if nothing else references them

## 4. Verify

- [x] 4.1 Run cloud frontend tests for touched specs
- [x] 4.2 Run cloud backend pickup-prefix / events tests if 1.4 added coverage
- [x] 4.3 Run `./scripts/lint.sh` (or staged) before commit
- [ ] 4.4 Manual: set Station in Stammdaten → Speichern → reload → still Station; Stationen shows letter fields; Kassen hides register letters
