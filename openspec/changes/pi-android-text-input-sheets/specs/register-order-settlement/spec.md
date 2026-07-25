## ADDED Requirements

### Requirement: Collective-bill create from list matches assign naming UX

Creating a Sammelrechnung from the open collective-bills list SHALL use the same in-app Name-entry sheet UX as creating a Sammelrechnung while assigning open positions from the settle screen. The list create path MUST NOT use a browser `window.prompt` dialog.

#### Scenario: Register or waiter creates from list

- **WHEN** a cashier or waiter creates a new Sammelrechnung from the open collective-bills list (event not in instant mode)
- **THEN** the Name-entry sheet matches the assign-flow create sheet (Name label, text field, primary create action)
- **AND** after successful create the settlement screen for that bill is shown as today
