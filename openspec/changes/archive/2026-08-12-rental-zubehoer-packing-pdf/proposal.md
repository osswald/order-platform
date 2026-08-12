## Why

Warehouse and field staff need a printable packing and return checklist per rental: which appliances go out, plus consumables and small items (Zubehör) such as paper rolls and network cables. Today rentals only track devices; there is no tenant catalog of recurring extras, no way to attach ad-hoc lines to a rental, and no PDF.

## What Changes

- Add a **tenant-scoped Zubehör catalog** (name + optional default quantity) configurable under Verwaltung / Verleiher settings.
- Add **rental Zubehör lines**: manually picked from the catalog (label snapshotted) or entered as free text, each with an optional quantity. Catalog items are **not** auto-added when a rental is created.
- Extend the **rental edit dialog** with a Zubehör section and a **Download packing list** action.
- Add **`GET /rentals/{id}/packing-list.pdf`**: checklist PDF with Verleiher header, open appliance lendings, and Zubehör lines (checkbox column for pack-out / handover / return). No prices, no signature block.

## Capabilities

### New Capabilities

- `rental-zubehoer`: Tenant catalog CRUD and per-rental Zubehör lines (catalog pick + free text, optional quantity).
- `rental-packing-pdf`: Packing/handover/return checklist PDF for a rental.

### Modified Capabilities

- `rental-calendar`: Rental edit surface includes Zubehör management and PDF download (tenant admin only).

## Impact

- **Cloud backend**: new tables (`rental_zubehoer_catalog`, `rental_zubehoer_lines`), tenant-admin APIs, PDF document under `cloud/backend/app/pdf/`, Alembic migration.
- **Cloud frontend**: Zubehör catalog UI (tenant settings or section), rental edit Zubehör block, download button, i18n (de: Zubehör), help snippet.
- **OpenAPI**: export + regenerate frontend types.
- **Edge / Pi**: none.
- **Out of scope**: prices, stock/inventory, auto-defaults on rental create, signatures, linking Zubehör to POS articles, separate outbound vs return PDF variants.
