## ADDED Requirements

### Requirement: Rental edit includes Zubehör and packing list download

From the rentals calendar edit surface, a tenant admin SHALL be able to manage Zubehör lines on the rental (add from catalog, add free text, edit quantity, remove lines) and download the packing list PDF. These actions MUST NOT be available on the create-only flow unless the rental already exists (i.e. after save or in edit mode).

#### Scenario: Edit dialog shows Zubehör section

- **WHEN** a tenant admin opens a rental for edit from the calendar
- **THEN** the dialog includes a Zubehör section
- **AND** they can add lines from the tenant catalog or as free text

#### Scenario: Download PDF from edit dialog

- **WHEN** a tenant admin clicks download packing list in the rental edit dialog
- **THEN** the browser receives the packing list PDF for that rental
