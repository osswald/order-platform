## ADDED Requirements

### Requirement: Register settlement supports Sumup connected
When an event allows `sumup_connected`, the register payment screen SHALL offer Sumup connected as a payment method and SHALL use the cash register’s configured default SumUp reader for Cloud API checkout. Sumup (manual) remains available as an offline confirmation type when enabled. Stripe Terminal MUST NOT appear as a register payment method.

#### Scenario: Connected pay on register
- **WHEN** the cashier settles on the register payment screen with Sumup connected and the register has a default reader
- **THEN** the payment completes via SumUp Cloud API on that reader and is recorded as `sumup_connected`

#### Scenario: No Stripe Terminal on register
- **WHEN** the register payment screen lists payment types for an event after this change
- **THEN** `stripe_terminal` / Karte (Stripe) is not offered
