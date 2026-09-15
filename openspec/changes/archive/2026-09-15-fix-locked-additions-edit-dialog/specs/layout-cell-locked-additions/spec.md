## ADDED Requirements

### Requirement: Reopening a combo cell restores locked Zusätze in the editor

When an admin opens the App-Layouts cell editor for an existing cell that already has a non-empty `locked_addition_ids` list and still qualifies as a combo cell (exactly one base article, no vouchers), the editor SHALL show those locked Zusätze as selected in the checklist after the linked-Zusatz options for that base article have loaded. Transient article-tree selection states while the dialog is open (including an empty selection during tree mount or reload) MUST NOT clear those locked ids. The editor MUST clear locked ids when the operator intentionally makes the cell non-combo by selecting a second article, changing to a different single base article, or selecting any voucher.

#### Scenario: Reopen shows previously locked Zusätze checked

- **WHEN** an admin opens the cell editor for a saved combo cell whose `locked_addition_ids` are non-empty
- **THEN** after Zusatz options load, each previously locked Zusatz appears selected in the checklist

#### Scenario: Transient empty article selection does not wipe locked ids

- **WHEN** the cell editor is open on a combo cell with seeded locked ids and the article tree selection briefly becomes empty then returns to the same single base article
- **THEN** the locked ids remain and the checklist still shows those Zusätze selected once options are available

#### Scenario: Intentional second article still clears locked ids

- **WHEN** the operator had locked Zusätze for one article and then selects a second article
- **THEN** the locked set is cleared before save

#### Scenario: Intentional voucher selection still clears locked ids

- **WHEN** the operator had locked Zusätze for one article and then selects any voucher
- **THEN** the locked set is cleared before save

#### Scenario: Changing the base article clears locked ids

- **WHEN** the operator had locked Zusätze for one article and then selects a different single base article
- **THEN** the locked set is cleared before save
