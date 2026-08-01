## REMOVED Requirements

### Requirement: Stripe webhooks are signature-verified
**Reason**: Stripe webhooks are removed with Stripe.
**Migration**: Implement SumUp webhook verification (see ADDED requirement).

### Requirement: Edge Stripe Terminal actions require edge auth and event scope
**Reason**: Edge Stripe Terminal endpoints are removed.
**Migration**: Protect SumUp Cloud API edge checkout endpoints with the same edge auth and event-scope rules (see ADDED requirement).

## ADDED Requirements

### Requirement: SumUp webhooks are signature-verified
`POST` SumUp webhook endpoint(s) SHALL reject requests that lack a valid SumUp signature for the configured webhook secret. Unsigned or tampered payloads MUST NOT mutate payment or organisation state.

#### Scenario: Unsigned webhook is rejected
- **WHEN** a client posts to the SumUp webhook endpoint without a valid signature
- **THEN** the response is an error status
- **AND** no webhook-driven state change is committed

### Requirement: Edge SumUp Cloud API actions require edge auth and event scope
SumUp reader checkout, terminate, and status operations exposed under the edge API SHALL require the same valid edge credentials as other protected edge routes. Unauthenticated callers MUST NOT create or terminate checkouts. Operations MUST be limited to organisations/events permitted by the edge credential binding (no foreign-event checkouts).

#### Scenario: Checkout endpoint without edge credentials fails
- **WHEN** a client calls an edge SumUp checkout endpoint without valid edge credentials
- **THEN** the response is HTTP 401 or 403
- **AND** no SumUp reader checkout is created

#### Scenario: Checkout rejected for foreign event
- **WHEN** an authenticated edge client requests a SumUp checkout for an event outside its credential scope
- **THEN** the response is HTTP 404 or 403
- **AND** no checkout is created for that foreign event
