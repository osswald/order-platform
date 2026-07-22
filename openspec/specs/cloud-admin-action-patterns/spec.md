# cloud-admin-action-patterns Specification

## Purpose
Cloud admin free-form buttons share an outline-first visual language: outlined surface by default, intent via color (primary / secondary / danger), with consistent recipes for tables, form footers, dialogs, and event-config card removes.

## Requirements

### Requirement: Outline-first free-form buttons

Cloud admin free-form `v-btn` controls MUST render with the outlined surface. The Vuetify application default `VBtn.variant = outlined` MUST remain in effect. Free-form buttons MUST NOT use `variant="text"`, `variant="flat"`, or other non-outlined variants. Segmented `v-btn-toggle` controls are not free-form action buttons and are exempt from this requirement.

#### Scenario: Global default remains outlined

- **WHEN** the cloud frontend Vuetify instance is configured
- **THEN** `defaults.VBtn.variant` is `outlined`

#### Scenario: No free-form text or flat buttons

- **WHEN** a free-form action button is rendered in the cloud admin UI
- **THEN** it does not use `variant="text"` or `variant="flat"`

#### Scenario: Login primary CTA is outlined

- **WHEN** the Login submit button is shown
- **THEN** it uses the primary intent with an outlined surface (not flat/filled)

### Requirement: Button intents

Free-form action buttons MUST follow one of these intents:

- **primary:** `color="primary"`, outlined — create/save/apply/login and equivalent progressive actions
- **secondary:** outlined without error/primary emphasis — back, cancel, refresh, close, and equivalent neutral actions
- **danger:** `color="error"`, outlined — delete/remove and equivalent destructive actions

#### Scenario: Save uses primary

- **WHEN** a form exposes a Save (or equivalent submit) action
- **THEN** that control uses the primary intent

#### Scenario: Back or Cancel uses secondary

- **WHEN** a form or dialog exposes Back or Cancel
- **THEN** that control uses the secondary intent

#### Scenario: Delete uses danger

- **WHEN** a destructive delete/remove action is exposed as a free-form button
- **THEN** that control uses the danger intent (`color="error"`, outlined)

### Requirement: Table and form danger labels

In list tables (`#item.actions` or equivalent) and in form footers, danger actions MUST show a visible text label (e.g. translated `common.delete`). They MUST NOT be icon-only in those contexts.

#### Scenario: Table delete shows a label

- **WHEN** a data table row exposes a delete action
- **THEN** the control is an outlined danger button with a visible delete label

#### Scenario: Form footer delete shows a label

- **WHEN** an edit form footer exposes delete
- **THEN** the control is an outlined danger button with a visible delete label

### Requirement: Config-card outlined icon remove

In dense event-configuration (or equivalent) card headers, a remove control MAY be icon-only, but MUST still be outlined danger (`color="error"`, icon such as `mdi-delete`, outlined surface — not `variant="text"`).

#### Scenario: Config card remove is outlined icon

- **WHEN** an event config card header exposes remove
- **THEN** the control is an outlined danger icon button (not a text-variant icon button)

### Requirement: Screen action patterns

Cloud admin screens MUST arrange actions as follows when those regions exist:

- **Form footer:** secondary leave/cancel, optional danger delete, primary save (primary last among peer actions)
- **Table row actions:** danger delete per table/form danger rules
- **Dialog actions:** secondary cancel and primary confirm; if the dialog’s confirming action is destructive, use danger instead of primary
- **Config-card header:** outlined icon danger remove when removal is offered

#### Scenario: Dialog cancel and confirm

- **WHEN** a modal dialog offers Cancel and a non-destructive Confirm
- **THEN** Cancel uses secondary and Confirm uses primary, both outlined

#### Scenario: Form footer order

- **WHEN** a detail form footer includes Back and Save
- **THEN** Back is secondary and Save is primary
