# stripe-connect Specification

## Purpose
Organisation-scoped Stripe Connect onboarding and readiness for Terminal direct charges (Accounts v2 create/link/refresh, denormalized org flags, webhook/status semantics, and a 0.2% platform application fee on Terminal charges).

## Requirements

### Requirement: Organisation Connect account creation uses Accounts v2

The cloud backend SHALL create a Stripe connected account for an organisation that has no `stripe_account_id` using the Accounts v2 API (`POST /v2/core/accounts` or the SDK equivalent), not Accounts v1 `Account.create` with `type` Express/Custom/Standard. The created account MUST be configured for merchant card acceptance suitable for Terminal direct charges on the connected account. The account MUST store metadata linking `organisation_id` and `hire_company_id`.

#### Scenario: First Connect click creates a v2 account

- **WHEN** a tenant admin calls `POST /stripe/connect/organisations/{id}/account-link` for an organisation with no `stripe_account_id` and Stripe is configured
- **THEN** the backend creates a connected account via Accounts v2, persists the returned account id on the organisation, and returns an Account Link URL for onboarding

#### Scenario: Accounts v1 create path is not used

- **WHEN** a new connected account is created for Connect onboarding
- **THEN** the backend MUST NOT call Accounts v1 account creation with a legacy `type` of `express`, `custom`, or `standard`

### Requirement: Connect status reflects merchant readiness

The cloud backend SHALL expose Connect status for an organisation including `stripe_account_id`, `charges_enabled`, `payouts_enabled`, and `details_submitted`. When refreshing from Stripe, `charges_enabled` MUST be true only when the merchant card-payments capability is active. Terminal PaymentIntent creation gates that already require `stripe_charges_enabled` MUST continue to use the denormalized organisation flag updated by refresh and webhooks.

#### Scenario: Status before onboarding

- **WHEN** a tenant admin requests Connect status for an organisation with no Stripe account
- **THEN** the response includes a null `stripe_account_id` and `charges_enabled` false

#### Scenario: Refresh after capabilities become active

- **WHEN** a tenant admin refreshes Connect status for an organisation whose Stripe merchant `card_payments` capability is active
- **THEN** the organisation’s stored `stripe_charges_enabled` is true and the status response reports `charges_enabled` true

### Requirement: Account Link onboarding uses env return URLs

The cloud backend SHALL create an Account Link for the organisation’s Stripe account using return and refresh URLs from environment configuration (`STRIPE_CONNECT_RETURN_URL`, `STRIPE_CONNECT_REFRESH_URL`). Client-supplied return or refresh URLs MUST NOT be used as the redirect targets.

#### Scenario: Account link ignores client URLs

- **WHEN** a tenant admin posts an account-link request with optional body return/refresh URLs
- **THEN** the Account Link is created with the env-configured URLs (or the request fails with a validation error if those env vars are missing)

### Requirement: Stripe configuration errors remain distinct from Stripe API failures

When `STRIPE_SECRET_KEY` is missing, Connect mutating endpoints SHALL fail with a service-unavailable style configuration error. When Stripe rejects a request after configuration is present, the backend SHALL map that to a Stripe request-failed error without exposing secret material.

#### Scenario: Missing secret key

- **WHEN** Connect account-link is called and `STRIPE_SECRET_KEY` is not configured
- **THEN** the API responds with a configuration/unavailable error (not a successful Account Link)

### Requirement: Terminal direct charges remain on the connected account

After an organisation has `stripe_charges_enabled` and an event enables `stripe_terminal`, edge Terminal PaymentIntent creation SHALL continue to create `card_present` PaymentIntents on the organisation’s connected account. This change MUST NOT move Terminal settlement onto the platform account.

#### Scenario: Terminal PI still uses connected account

- **WHEN** an edge client creates a Terminal PaymentIntent for an event whose organisation has a ready Stripe account
- **THEN** the PaymentIntent is created on that organisation’s `stripe_account_id` with `payment_method_types` including `card_present`

### Requirement: Platform collects 0.2% application fee on Terminal charges

When creating a Terminal PaymentIntent, the cloud backend SHALL set Stripe `application_fee_amount` to **0.2%** (20 basis points) of the PaymentIntent `amount`, rounded half-up to the nearest currency minor unit. If the rounded fee is less than 1 minor unit, the backend MUST omit `application_fee_amount`. The fee MUST be strictly less than the charge amount. Cash, TWINT, and SumUp payments MUST NOT receive an application fee through this path.

#### Scenario: Fee on a typical Terminal amount

- **WHEN** the edge creates a Terminal PaymentIntent for 1000 minor units (e.g. CHF 10.00)
- **THEN** the PaymentIntent is created with `application_fee_amount` equal to 2 (0.2% of 1000)

#### Scenario: Fee omitted when it rounds to zero

- **WHEN** the edge creates a Terminal PaymentIntent for an amount whose 0.2% rounds to 0 minor units
- **THEN** the PaymentIntent is created without `application_fee_amount`
