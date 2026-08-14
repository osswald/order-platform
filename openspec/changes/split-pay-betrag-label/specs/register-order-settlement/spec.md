## ADDED Requirements

### Requirement: Split-pay green bar amount label
The shared Pi split-pay settle screen (waiter table settle and register order settle) SHALL label the green pay control with **Betrag** when no open line quantities remain unselected (nothing left in the bottom / remaining panel for the current open bill), and with **Teilbetrag** when at least one open line quantity remains unselected. The payable amount shown next to that label SHALL continue to reflect the selected basket (after voucher credit) as today. Settlement behavior MUST NOT change based on the label wording alone.

#### Scenario: Full selection of open lines shows Betrag
- **WHEN** a waiter or register operator has moved all currently open line quantities into the top (pay) panel so remaining open quantity is zero
- **THEN** the green pay control is labeled **Betrag** followed by the payable amount

#### Scenario: Partial selection shows Teilbetrag
- **WHEN** at least one open line quantity remains in the bottom (remaining) panel
- **THEN** the green pay control is labeled **Teilbetrag** followed by the payable amount for the selection
