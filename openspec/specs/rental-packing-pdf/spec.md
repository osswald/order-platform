# rental-packing-pdf Specification

## Purpose

Provides a downloadable packing and return checklist PDF for a rental so warehouse and field staff can verify appliances and Zubehör without prices or signatures.

## Requirements

### Requirement: Packing list PDF for a rental

The system SHALL expose a tenant-admin endpoint that returns a PDF packing list for a rental. The PDF MUST include Verleiher identification (name and address where configured), rental display name, organisation name, and inclusive rental dates formatted for the admin locale and organisation country. The PDF MUST NOT include prices or a signature block.

#### Scenario: Download packing list PDF

- **WHEN** a tenant admin requests the packing list PDF for a rental in their Verleiher
- **THEN** the response is `application/pdf` with a sensible filename
- **AND** the body contains the rental header information

#### Scenario: Organisation user cannot download the PDF

- **WHEN** an organisation user requests the packing list PDF
- **THEN** the system rejects the request as forbidden

### Requirement: PDF lists open appliances as a checklist

The PDF MUST include a **Geräte** section listing each open appliance lending on the rental (`returned_at` is null). Each row MUST show appliance name and type (or equivalent identification) and MUST include a checkbox column suitable for manual pack-out and return verification. Returned lendings MUST NOT appear in this section.

#### Scenario: Open lendings appear with checkboxes

- **WHEN** a rental has two open lendings and one returned lending
- **THEN** the PDF Geräte section lists exactly the two open appliances
- **AND** each row has a checkbox placeholder

#### Scenario: Rental with no devices still produces a PDF

- **WHEN** a rental has no open lendings
- **THEN** the PDF is still generated
- **AND** the Geräte section indicates there are no devices or is empty with a clear label

### Requirement: PDF lists rental Zubehör lines

The PDF MUST include a **Zubehör** section listing all Zubehör lines on the rental in sort order. Each row MUST include a checkbox column and the line label. When a line has a quantity, the PDF MUST print it; when quantity is not set, the PDF MUST omit the quantity (no placeholder, em dash, or invented number).

#### Scenario: Zubehör lines with and without quantity

- **WHEN** a rental has lines "Thermopapier" quantity 2 and "Netzwerkkabel" with no quantity
- **THEN** both appear in the Zubehör section with checkboxes
- **AND** "Thermopapier" shows quantity 2
- **AND** "Netzwerkkabel" shows no quantity
