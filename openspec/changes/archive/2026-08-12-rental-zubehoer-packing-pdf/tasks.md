## 1. Schema and models

- [x] 1.1 Write failing tests: catalog CRUD tenant scope; rental lines manual add; no auto-lines on rental create; label snapshot on catalog pick; free-text line without catalog_id
- [x] 1.2 Add Alembic migration: `rental_zubehoer_catalog`, `rental_zubehoer_lines` with FKs, indexes, ON DELETE SET NULL for catalog on lines
- [x] 1.3 Add SQLAlchemy models and relationships on `HireCompany` / `Rental`

## 2. Zubehör API

- [x] 2.1 Write failing tests: catalog list/create/update/delete; rental zubehoer-lines CRUD; include lines on `GET /rentals/{id}`; org user forbidden
- [x] 2.2 Implement tenant-admin catalog router (scoped to active Verleiher)
- [x] 2.3 Implement nested `/rentals/{id}/zubehoer-lines` CRUD; extend `RentalRead` with `zubehoer_lines`
- [x] 2.4 Export OpenAPI and regenerate cloud frontend types

## 3. Packing list PDF

- [x] 3.1 Write failing tests: PDF endpoint auth; open lendings only; zubehoer lines print quantity only when set; no prices in output (smoke/structure)
- [x] 3.2 Implement `build_rental_packing_pdf` using `VqPdf` + i18n keys `pdf.rental_packing.*`
- [x] 3.3 Add `GET /rentals/{id}/packing-list.pdf` returning `pdf_download_response`

## 4. Frontend

- [x] 4.1 Write failing tests: catalog section on tenant settings; rental edit zubehoer add/remove; PDF download trigger
- [x] 4.2 Add Zubehör catalog UI on Verleiher-Einstellungen (name, optional default qty, active/sort)
- [x] 4.3 Extend rental edit dialog: Zubehör list, pick from catalog, free text, optional qty, delete line
- [x] 4.4 Add “Packing list PDF” download in edit dialog
- [x] 4.5 Add de/en i18n (Zubehör / Accessories) and help updates

## 5. Verification

- [x] 5.1 Run cloud backend tests
- [x] 5.2 Run cloud frontend tests and typecheck
- [x] 5.3 Run `./scripts/lint.sh`
