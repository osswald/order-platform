## Why

On the Pi split-pay settle screen, the green pay button always says **Teilbetrag**, even when every open line is selected and Rest is `CHF 0.00`. That word only makes sense for a true partial payment; for a full (or full-remaining) settle it should say **Betrag**.

## What Changes

- Show **Betrag** on the green pay bar when nothing remains below (full selection of currently open lines)
- Keep **Teilbetrag** when some open lines stay in the bottom panel (true split)
- Update Pi settle-screen tests accordingly
- No API or settlement semantics changes

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `register-order-settlement`: Clarify green pay-bar label wording for full vs partial selection on the shared split-pay settle UI (register and waiter)

## Impact

- `pi/frontend/src/components/SplitPaySettleScreen.vue` (and its unit test)
- Waiter table settle and register order settle share this component — both get the label fix
- No backend, OpenAPI, or i18n catalog changes (copy is currently hardcoded German in the component)
