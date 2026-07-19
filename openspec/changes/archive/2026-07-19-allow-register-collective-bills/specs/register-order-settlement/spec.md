## MODIFIED Requirements

### Requirement: Register hub exposes Sammelrechnungen like the waiter hub
The register UI SHALL provide a Sammelrechnungen action on the cash register hub. A valid cash-register session SHALL be authorized to access the open collective-bills list and collective-bill settlement screens for the current event, with the same list, create, open, and settle capabilities as a valid waiter session. If neither a cash-register session nor a waiter session is active, the collective-bill routes SHALL require operator login.

#### Scenario: Open collective bills from register hub
- **WHEN** a cashier with a valid cash-register session taps Sammelrechnungen on the register hub
- **THEN** the open collective-bills screen is shown for the current event without redirecting to waiter login

#### Scenario: Create collective bill from register context
- **WHEN** the cashier creates a new Sammelrechnung after entering from the register hub and the event is not in instant payment mode
- **THEN** the bill is created and the settlement screen for that bill is shown, as for waiters

#### Scenario: Open and settle collective bill from register context
- **WHEN** the cashier opens an existing Sammelrechnung after entering from the register hub
- **THEN** the collective-bill settlement screen is shown and the cashier can settle the bill with the same settlement capabilities as a waiter

#### Scenario: Waiter retains collective-bill access
- **WHEN** a waiter with a valid waiter session opens the collective-bills list or settlement screen
- **THEN** access is allowed as before

#### Scenario: Collective-bill access requires an operator
- **WHEN** neither a waiter session nor a cash-register session is active and a collective-bill route is requested
- **THEN** access is denied and the operator is redirected to login with the requested route preserved
