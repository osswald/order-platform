## ADDED Requirements

### Requirement: Payment type Sumup connected
The platform payment-type allowlist SHALL include slug `sumup_connected` with display label **Sumup connected**. The existing slug `sumup` SHALL remain and display as **Sumup (manual)** for offline confirmation without calling SumUp APIs. The slug `stripe_terminal` SHALL NOT remain an active payment type.

#### Scenario: Manual vs connected
- **WHEN** an event enables both `sumup` and `sumup_connected`
- **THEN** the POS shows distinct labels Sumup (manual) and Sumup connected

#### Scenario: Stripe terminal deactivated
- **WHEN** payment types are seeded or refreshed after this change
- **THEN** `stripe_terminal` is not an active selectable payment type for new event configuration

### Requirement: Cash register default SumUp reader
When cash registers are configured for an event, each cash register MAY have a default SumUp reader chosen from the organisation’s labelled readers. Settlements that use `sumup_connected` on that register SHALL target the register’s default reader. If `sumup_connected` is enabled and no default is set while multiple readers exist, the register UI MUST require a default (or block connected card pay) before charging.

#### Scenario: Register uses default reader
- **WHEN** a cashier pays with Sumup connected on a register that has a default reader
- **THEN** the Cloud API checkout is started on that reader

### Requirement: Waiter selects SumUp device at login
When waiter mode is used and the event allows `sumup_connected`, the waiter login flow SHALL let the waiter choose a SumUp device from the organisation’s reader labels (auto-select when exactly one reader exists). The selection SHALL persist for the waiter session and be used for subsequent Sumup connected payments until login changes it.

#### Scenario: Login picker
- **WHEN** a waiter logs in for an event with `sumup_connected` and more than one org reader
- **THEN** login requires selecting a labelled SumUp device before continuing

#### Scenario: Single reader auto-select
- **WHEN** a waiter logs in and the organisation has exactly one paired reader
- **THEN** that reader is selected without requiring a manual pick

### Requirement: Edge Cloud API checkout lifecycle
For `sumup_connected` payments, the Pi SHALL call cloud edge endpoints that create a SumUp reader checkout for the event’s organisation merchant and selected reader, include the platform Affiliate Key metadata, support terminate while awaiting cardholder action, and confirm success via verified webhook and/or status polling before recording the payment. The recorded payment MUST include type `sumup_connected`, amount, and a SumUp transaction/checkout identifier. The system MUST NOT attach a platform application fee amount to the charge.

#### Scenario: Successful connected payment
- **WHEN** a waiter or cashier completes Sumup connected pay and the Solo checkout succeeds
- **THEN** the order payment is stored as `sumup_connected` with a SumUp transaction identifier and the amount charged

#### Scenario: Terminate checkout
- **WHEN** the POS cancels an in-progress Sumup connected payment while the reader awaits cardholder action
- **THEN** the cloud requests SumUp terminate for that reader and the order is not marked paid for that attempt

#### Scenario: No platform fee
- **WHEN** a SumUp reader checkout is created
- **THEN** no Vendiqo platform application-fee field is applied to the charge
