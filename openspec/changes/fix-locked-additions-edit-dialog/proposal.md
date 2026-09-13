## Why

When an admin reopens a layout cell that already has locked Zusätze (`locked_addition_ids`), the cell editor does not show those selections as checked. Persistence and API round-trips look correct; the edit dialog can clear seeded ids when article/voucher selection briefly looks ineligible (e.g. treeview mount). That makes saved combo buttons look broken and risks overwriting real locks with `[]` if the admin Applies/saves after reopen.

## What Changes

- Preserve seeded `locked_addition_ids` when opening an existing combo cell for edit until the operator *intentionally* changes the base article or adds vouchers / a second article.
- Stop treating transient ineligible selection (empty tree selection during mount/load) as a reason to wipe locked ids.
- Still clear locked ids when the cell becomes durably non-combo (multiple articles or any voucher), matching existing rules.
- Add frontend coverage so reopen-with-real selection churn cannot regress unchecked locks.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `layout-cell-locked-additions`: Strengthen admin editor requirements so reopening a saved combo cell restores previously locked Zusätze in the checklist, and so locked ids are cleared only on intentional eligibility loss—not on transient UI selection noise.

## Impact

- Cloud frontend: `EventConfigLayoutsSection.vue` (open dialog + locked-additions watcher / clear helpers) and related Vitest cases.
- No backend schema, API, or Pi POS behaviour changes expected unless investigation proves a separate persistence gap (out of scope for this fix).
- Spec archive for the original feature remains; this is a behaviour gap in the admin editor requirement.
