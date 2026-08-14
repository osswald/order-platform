## Why

On the Pi POS order screen, **Position wählen** (`LayoutCellPickerSheet`) looks smaller than **Zusätze** (`AdditionsPickerSheet`): list rows are native `<button>`s that do not inherit type size, and the footer control does not match the Zusätze action buttons. Separately, the waiter/register TWINT QR sheet is meant to be fullscreen but inherits `max-height: 70vh` from `.sheet`, so Fertig/Abbrechen sit mid-screen and the QR stays capped at 360px. On the customer display, the TWINT QR image can overflow the rounded grey panel border.

## What Changes

- Make **Position wählen** option rows use the same font size and tap-target size as **Zusätze** option rows
- Make **Position wählen** **Abbrechen** the same size as the Zusätze **Abbrechen** / **Übernehmen** buttons
- Make the waiter/register TWINT QR sheet fill the viewport on web and Android, with **Fertig** and **Abbrechen** pinned to the bottom (safe-area insets unchanged)
- Scale the waiter/register TWINT QR image to fill the remaining space between amount and actions, with margin on all sides
- Keep the customer-display TWINT QR inside the rounded grey panel border
- No API, payment, or order-flow changes

## Capabilities

### New Capabilities

- `pi-pos-order-sheets`: Shared visual sizing for POS order picker sheets (layout-cell picker vs additions); viewport-filling waiter/register TWINT QR layout; customer-display TWINT QR clipped to the panel border

### Modified Capabilities

- `pi-android-safe-layout`: TWINT QR sheet fills the Android WebView height (not a partial overlay); Fertig/Abbrechen stay at the bottom of the safe area

## Impact

- `pi/frontend/src/components/LayoutCellPickerSheet.vue`
- `pi/frontend/src/styles/app.css` (shared `.sheet` / `.sheet-option-row` / `.sheet--picker` rules)
- `pi/frontend/src/components/TwintQrSheet.vue`
- `pi/frontend/src/views/RegisterDisplayView.vue` (customer-display TWINT panel)
- Contract tests for picker rows, TWINT sheet layout, and customer-display QR overflow
- Waiter table order and register Abholkasse share the picker and TWINT sheet
- Hosted Cloud-Pi wide demo still constrains sheet **width** to the Pi column; height must fill that column
- No backend, OpenAPI, or native Android UI (WebView hosts the same Vue sheet)
