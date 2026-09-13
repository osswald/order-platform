## Why

`pickup_prefix_mode` is an event-level field already saved with Stammdaten, but the **Abholcode-Buchstabe von** control lives on Stationen/Kassen and is persisted via a fragile configuration-autosave + second event PUT. Operators choose “Station” and it falls back to “Kasse” after reload. Moving the control to Stammdaten aligns UI with the data model and uses the reliable manual Save path.

## What Changes

- Move the **Abholcode-Buchstabe von** dropdown from Stationen and Kassen into event **Stammdaten** (Konfiguration group), with the same lock when status ≠ `config`.
- Persist mode only via the existing Stammdaten Save (`PUT /events/{id}` with full event payload including `pickup_prefix_mode`).
- Remove mode from configuration autosave (no second partial event PUT; drop `pickupPrefixModeSaved` / baseline-patch bridge).
- Keep Stationen/Kassen **letter** fields show/hide based on mode (read-only prop from parent); remove duplicate mode dropdowns from those sections.
- Add a frontend (and if missing, backend) round-trip test so choosing Station and saving Stammdaten survives reload.

## Capabilities

### New Capabilities

<!-- none — this corrects placement/persistence of an existing capability -->

### Modified Capabilities

- `pickup-prefix-mode`: Mode control SHALL live in Stammdaten and SHALL persist with Stammdaten Save; Stationen/Kassen SHALL only show active-mode prefix letter fields (not the mode select).

## Impact

- **Cloud frontend**: `EventStammdatenFields`, `EventConfigStationsSection`, `EventConfigCashRegistersSection`, `EventConfiguration.vue`, `Events.vue`, `eventDetailSave` helpers, i18n placement, unit tests.
- **Cloud backend**: No schema change expected; optional HTTP round-trip coverage for mode update if not already present.
- **Pi / edge**: Unchanged (mode semantics and allocation stay as today).
