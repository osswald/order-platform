## MODIFIED Requirements

### Requirement: PDF lists open appliances as a checklist

The PDF MUST include a **Geräte** section listing each open appliance lending on the rental (`returned_at` is null). Each row MUST show appliance name and a localized appliance type label (admin locale), MUST include the appliance IP address when known, and MUST include a checkbox column suitable for manual pack-out and return verification. Open appliances MUST be ordered by type in the stable order server → router → ap → printer → mobile → tablet (then any other types), with a deterministic secondary order within a type. Returned lendings MUST NOT appear in this section.

#### Scenario: Open lendings appear with checkboxes

- **WHEN** a rental has two open lendings and one returned lending
- **THEN** the PDF Geräte section lists exactly the two open appliances
- **AND** each row has a checkbox placeholder

#### Scenario: Printer IP appears on the PDF row

- **WHEN** an open printer lending has an IP address configured
- **AND** a tenant admin downloads the packing list PDF
- **THEN** that appliance’s Geräte row includes the IP address

#### Scenario: Type labels are localized

- **WHEN** the packing list is generated with German admin locale
- **THEN** appliance type labels use the German type strings (e.g. Drucker for printer)

#### Scenario: Rental with no devices still produces a PDF

- **WHEN** a rental has no open lendings
- **THEN** the PDF is still generated
- **AND** the Geräte section indicates there are no devices or is empty with a clear label
