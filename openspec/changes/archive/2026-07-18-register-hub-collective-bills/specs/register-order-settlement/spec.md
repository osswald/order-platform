## ADDED Requirements

### Requirement: Register hub exposes Sammelrechnungen like the waiter hub
The register UI SHALL provide a Sammelrechnungen action on the cash register hub that opens the open collective-bills list for the current event, using the same list/create/open capabilities as the waiter hub entry.

#### Scenario: Open collective bills from register hub
- **WHEN** the cashier taps Sammelrechnungen on the register hub
- **THEN** the open collective-bills screen is shown for the current event

#### Scenario: Create collective bill from register context
- **WHEN** the cashier creates a new Sammelrechnung after entering from the register hub (and the event is not in instant payment mode)
- **THEN** the bill is created and the settle screen for that bill is shown, as for waiters

### Requirement: Collective-bill navigation returns to the register hub
When the open collective-bills flow is entered from the register hub, back navigation SHALL return to that register hub (not the waiter hub). Leaving a collective settle screen SHALL return to the open collective-bills list while preserving register return context.

#### Scenario: Back from collective list to register hub
- **WHEN** the cashier opens Sammelrechnungen from the register hub and then navigates back from the list
- **THEN** the register hub for the same register is shown

#### Scenario: Back from collective settle keeps register context
- **WHEN** the cashier opens a Sammelrechnung from the register-entered list and navigates back from settle
- **THEN** the open collective-bills list is shown and a further back still returns to the register hub
