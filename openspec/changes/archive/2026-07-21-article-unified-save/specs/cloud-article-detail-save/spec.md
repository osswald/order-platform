## ADDED Requirements

### Requirement: Article detail uses a single Save action

The cloud admin article detail form SHALL expose one primary Save control for persisting the article and its applicable nested link data. The form MUST NOT expose separate Save controls for additions or ingredients.

#### Scenario: Nested save buttons are absent

- **WHEN** an operator opens an existing article detail that shows additions and/or ingredients sections
- **THEN** the UI does not show dedicated “Save additions” or “Save ingredients” buttons
- **AND** a single primary Save control is available for the form

#### Scenario: Edit save persists article and applicable links

- **WHEN** an operator edits article fields and/or addition and/or ingredient links on an existing article detail
- **AND** they activate Save
- **THEN** the system persists the article fields
- **AND** when the additions section applies, the system persists the current addition links
- **AND** when the ingredients section applies, the system persists the current ingredient links

#### Scenario: Create save persists only the article then enables nested sections

- **WHEN** an operator creates a new article and activates Save
- **THEN** the system creates the article
- **AND** the additions and ingredients sections become available on the resulting detail when they apply for that article and organisation (same visibility rules as today)

### Requirement: Successful Save stays on article detail

After a successful article create or update Save, the cloud admin UI MUST keep the operator on that article’s detail view. Returning to the list MUST remain available via the existing Back (or equivalent leave) action, not via successful Save.

#### Scenario: Update stays on detail

- **WHEN** an operator successfully Saves changes on an existing article detail
- **THEN** the UI remains on that article’s detail
- **AND** a success indication is shown

#### Scenario: Create navigates to the new article detail

- **WHEN** an operator successfully Saves a new article
- **THEN** the UI shows the detail for the newly created article (not the list)
- **AND** a success indication is shown

### Requirement: Failed Save is all-or-nothing in UX terms

If any step of the Save sequence fails, the overall Save MUST be treated as failed: the UI MUST stay on the article detail, MUST NOT show a success indication for the overall Save, and MUST show one comprehensible error that identifies the failed concern (article, additions, or ingredients) when that distinction is known.

#### Scenario: Link persistence failure after article update

- **WHEN** an operator Saves an existing article
- **AND** the article update succeeds
- **AND** a subsequent additions or ingredients persistence step fails
- **THEN** the UI remains on the article detail
- **AND** the UI does not show an overall success message
- **AND** the UI shows an error message that makes the failed step comprehensible

#### Scenario: Article persistence failure

- **WHEN** an operator activates Save
- **AND** creating or updating the article fails
- **THEN** the UI remains on the current detail (create or edit)
- **AND** the UI shows an error for the article save failure
- **AND** nested link persistence is not presented as successful
