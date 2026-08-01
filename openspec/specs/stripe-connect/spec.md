# stripe-connect Specification

## Purpose
Retired. Card acceptance moved from Stripe Connect to per-organisation SumUp OAuth and Cloud API. See `sumup-cloud-connect` (OAuth linking on SumUp-Geräte) and `sumup-cloud-payments` (Solo reader checkouts on the organisation merchant).

## Requirements

### Requirement: Stripe Connect is retired
The product SHALL NOT offer Stripe Connect organisation onboarding, Account Links, Connect readiness APIs, Terminal PaymentIntent creation on connected accounts, or a Vendiqo platform application fee on card charges. Card acceptance SHALL use SumUp OAuth and Cloud API instead (`sumup-cloud-connect`, `sumup-cloud-payments`).

#### Scenario: No Stripe Connect onboarding
- **WHEN** an organisation manager seeks card-acceptance setup in cloud admin
- **THEN** the product does not offer Stripe Connect account creation or Account Links
- **AND** SumUp OAuth connect via SumUp-Geräte is the supported path

#### Scenario: No platform application fee on card charges
- **WHEN** a card-present payment is created for an organisation merchant
- **THEN** no Stripe `application_fee_amount` or equivalent Vendiqo platform fee is applied
- **AND** settlement uses SumUp Cloud API reader checkout, not Stripe Terminal PaymentIntents
