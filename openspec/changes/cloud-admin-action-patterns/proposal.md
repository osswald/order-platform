## Why

Cloud admin buttons render inconsistently: the same actions (especially delete) appear as outlined labels, text-only labels, or icon-only trash controls across list tables, form footers, and event-config cards. Vuetify already defaults `VBtn` to `outlined`, but call sites override with `text` / `flat`, so the UI drifts. Establishing a thin action vocabulary and migrating every button keeps the admin chrome predictable without building a full design system.

## What Changes

- Document outline-first action principles for the cloud frontend (color carries intent; no fill-based hierarchy).
- Define three button intents — primary, secondary, danger — plus rules for icon-only outlined removes and `v-btn-toggle` (unchanged).
- Define four screen patterns: form footer, table `#item.actions`, config-card header remove, dialog actions.
- Migrate all cloud frontend `v-btn` call sites to those recipes (including Login and former text/flat/icon overrides).
- Keep `defaults.VBtn.variant = 'outlined'` in `cloud/frontend/src/main.ts`; remove unnecessary `variant` overrides that fight the default.
- Out of scope: component wrappers, Storybook, design tokens, Pi frontend, non-button Vuetify controls.

## Capabilities

### New Capabilities

- `cloud-admin-action-patterns`: Outline-first button intents and screen action patterns for the cloud admin UI, including migration constraints for `v-btn` variants.

### Modified Capabilities

- (none)

## Impact

- **Cloud frontend only**: ~167 `v-btn` usages across list/detail screens, event config sections, dialogs, Login, Hosted Pi, and related components.
- **No API / backend / OpenAPI** changes.
- **Visual-only** for most screens; behavior (confirm dialogs, click handlers) unchanged.
- Tests: update any component tests that assert specific `variant` / class markup; no new backend tests.
