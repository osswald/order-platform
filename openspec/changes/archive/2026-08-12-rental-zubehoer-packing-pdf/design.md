## Context

See proposal.md. Rentals already exist with `ApplianceLending` children; the edit dialog and `GET/PATCH /rentals/{id}` are in place (PR #279). Cloud PDFs use `VqPdf` (fpdf2) and hire-company receipt logo assets (collective bill pattern).

## Goals / Non-Goals

**Goals:**
- Tenant catalog of Zubehör items for quick picking when editing a rental.
- Per-rental lines: catalog-backed (name snapshot) or free text; optional quantity on catalog default and on each line.
- One checklist PDF for packing and return verification.

**Non-Goals:**
- Auto-copy catalog defaults onto new rentals.
- Prices, inventory deduction, signatures.
- POS article / ingredient linkage.
- Org-user access to catalog or PDF.

## Decisions

### 1. Two tables: catalog vs rental lines

**Choice:**

| Table | Scope | Fields (conceptual) |
|-------|--------|---------------------|
| `rental_zubehoer_catalog` | `hire_company_id` | `name`, `default_quantity` (nullable int), `sort_order`, `is_active` |
| `rental_zubehoer_lines` | `rental_id` | `catalog_item_id` (nullable FK), `label` (required), `quantity` (nullable int), `sort_order` |

**Why:** Catalog is reusable configuration; lines are the rental-specific fact for PDF and history. Nullable `catalog_item_id` distinguishes free-text lines. `label` is copied from catalog name on pick so renames do not rewrite old rentals.

**Alternatives:** JSON blob on `rentals` (no catalog reuse); only free text (no picker).

### 2. No auto-add on rental create

**Choice:** Creating a rental does not insert any Zubehör lines. Operators add lines explicitly in the edit dialog.

**Why:** User requirement; avoids surprise lines on empty calendar creates.

### 3. Quantity optional everywhere

**Choice:** Catalog `default_quantity` and line `quantity` are both nullable. On the PDF, quantity is printed only when set; unset quantity is omitted entirely (no placeholder).

**Why:** Some items are “as needed” without a fixed count; empty quantity cells add noise on the checklist.

### 4. API shape

**Choice:**

- `GET/POST/PATCH/DELETE /rental-zubehoer-catalog/` (or under `/hire-companies/{id}/zubehoer`) — tenant admin, scoped to active Verleiher.
- `GET/POST/PATCH/DELETE /rentals/{id}/zubehoer-lines` — tenant admin; include lines on `RentalRead` or nested resource only (prefer nested CRUD + include in `GET /rentals/{id}` for edit dialog).

**Why:** Keeps rental container API cohesive; catalog is separate admin surface.

### 5. PDF content and lendings filter

**Choice:** `GET /rentals/{id}/packing-list.pdf` returns `application/pdf`. Sections:

1. Header: Verleiher name/address, rental display name, organisation, date range (locale-formatted).
2. **Geräte**: open lendings only (`returned_at IS NULL`), grouped by appliance type, checkbox column.
3. **Zubehör**: lines in sort order, checkbox + label + quantity (only when set).

Reuse `VqPdf`, hire-company logo via existing receipt logo fields. i18n via `pdf.rental_packing.*` keys (de/en).

**Why:** Return checklist uses same sheet; returned devices are not listed.

**Alternatives:** Include planned-only vs current segments in PDF — v1 lists all open lendings regardless of segment.

### 6. UI placement

**Choice:**
- **Zubehör-Katalog**: new section on `TenantSettings.vue` (Verleiher-Einstellungen), same audience as receipt templates.
- **Rental edit**: Zubehör list + “Add from catalog” + “Add free text”; PDF download button in dialog actions.

**Why:** Matches existing Verwaltung patterns; no new top-level nav for v1.

## Risks / Trade-offs

- **[Catalog orphan lines]** → If catalog row deleted, rental lines keep `label`; `catalog_item_id` SET NULL on delete.
- **[Empty PDF]** → Valid: rental with no devices and no Zubehör still produces a header-only checklist.
- **[PDF locale]** → Use admin UI locale + organisation country for date formatting (same as other cloud PDFs).

## Migration Plan

1. Alembic: create catalog + lines tables; FKs and indexes on `hire_company_id`, `rental_id`.
2. Deploy API + UI.
3. Export OpenAPI in same PR.

No Pi/edge changes.

## Open Questions

_(none — quantity optional, no auto-add, no signature locked in exploration)_
