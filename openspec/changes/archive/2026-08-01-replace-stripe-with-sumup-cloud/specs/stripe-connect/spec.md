## REMOVED Requirements

### Requirement: Organisation Connect account creation uses Accounts v2
**Reason**: Card acceptance moves from Stripe Connect to per-organisation SumUp OAuth and Cloud API.
**Migration**: Use `sumup-cloud-connect` OAuth linking on SumUp-Geräte; remove Stripe Connect account creation APIs and org `stripe_account_id` usage for new onboarding.

### Requirement: Connect status reflects merchant readiness
**Reason**: Stripe Connect readiness flags are retired with Stripe.
**Migration**: Expose SumUp connection status (merchant linked + token health) via SumUp-Geräte / connect APIs.

### Requirement: Account Link onboarding uses env return URLs
**Reason**: Stripe Account Links are removed.
**Migration**: Use SumUp OAuth authorize/callback URLs configured for the platform OAuth app.

### Requirement: Stripe configuration errors remain distinct from Stripe API failures
**Reason**: Stripe is removed from the product.
**Migration**: Apply analogous configuration-vs-API error distinction for SumUp OAuth/client env (`SUMUP_*`).

### Requirement: Terminal direct charges remain on the connected account
**Reason**: Stripe Terminal PaymentIntents are replaced by SumUp Solo reader checkouts on the organisation’s SumUp merchant.
**Migration**: Implement `sumup-cloud-payments` edge checkout against the org merchant + paired reader.

### Requirement: Platform collects 0.2% application fee on Terminal charges
**Reason**: Product decision to drop platform application fees on card payments.
**Migration**: Do not set Stripe `application_fee_amount` or any Vendiqo platform fee on SumUp checkouts; Affiliate Key is for attribution only.
