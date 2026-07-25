## ADDED Requirements

### Requirement: Edge pairing requires a valid short-lived code
`POST /edge/v1/pair` SHALL succeed only when the supplied pairing code matches an active, non-expired, unused pairing session and meets the documented format (normalized 6-digit code). Invalid, expired, or already-consumed codes MUST fail without issuing edge credentials.

#### Scenario: Invalid pairing code is rejected
- **WHEN** a client posts `/edge/v1/pair` with a pairing code that is not active
- **THEN** the response is HTTP 401 (or equivalent unauthorized)
- **AND** no edge client id or secret is issued

#### Scenario: Valid pairing issues credentials once
- **WHEN** a client posts `/edge/v1/pair` with a valid active pairing code
- **THEN** the response includes an edge client id and secret
- **AND** a subsequent pair attempt with the same code fails

### Requirement: Edge pairing attempts are rate-limited
The cloud backend SHALL rate-limit edge pairing attempts to constrain online guessing of pairing codes.

#### Scenario: Excess pair attempts are rejected
- **WHEN** a client exceeds the configured edge pair rate limit
- **THEN** subsequent pair attempts receive HTTP 429

### Requirement: Edge API requests require valid client credentials
Authenticated `/edge` routes (other than pair) SHALL require valid `X-Edge-Client-Id` and `X-Edge-Secret` headers corresponding to a non-revoked edge credential. Missing, wrong, or revoked credentials MUST NOT authorize bundle download, order ingest, sync, Terminal, or unpair-as-authenticated operations.

#### Scenario: Missing edge headers are rejected
- **WHEN** a client calls a protected `/edge` route without valid edge credentials
- **THEN** the response is HTTP 401 or 403
- **AND** no privileged side effect occurs

#### Scenario: Revoked edge credentials are rejected
- **WHEN** edge credentials have been revoked or unpaired
- **AND** a client presents those credentials to a protected `/edge` route
- **THEN** the response is HTTP 401 or 403

### Requirement: Edge credentials are scoped to their lending organisation
An authenticated edge client MUST only access event bundles, order ingest, and related edge operations for organisations/events permitted by its credential binding. The edge client MUST NOT read or mutate another hire company's or unbound organisation's data by supplying foreign ids.

#### Scenario: Edge client cannot ingest for foreign organisation event
- **WHEN** an edge client authenticated for organisation O attempts an edge operation targeting an event that belongs only to another organisation
- **THEN** the response is HTTP 404 or 403
- **AND** no order or config mutation for that foreign event is persisted

### Requirement: Tenant admins can revoke edge credentials
Authorized appliance/tenant administrators SHALL be able to revoke edge credentials (and complete unpair flows) so that a lost or compromised device can be cut off without rotating unrelated secrets. After revoke, prior credentials MUST fail authentication as specified above.

#### Scenario: Revoke disables further edge API use
- **WHEN** an authorized admin revokes an edge credential
- **AND** the former client calls a protected `/edge` route with the old secret
- **THEN** the response is HTTP 401 or 403

### Requirement: Stripe webhooks are signature-verified
`POST /stripe/webhooks` SHALL reject requests that lack a valid Stripe signature for the configured `STRIPE_WEBHOOK_SECRET`. Unsigned or tampered payloads MUST NOT mutate payment or organisation state.

#### Scenario: Unsigned webhook is rejected
- **WHEN** a client posts to `/stripe/webhooks` without a valid Stripe signature
- **THEN** the response is an error status
- **AND** no webhook-driven state change is committed

### Requirement: Edge Stripe Terminal actions require edge auth and event scope
Stripe Terminal connection tokens and PaymentIntent operations exposed under the edge API SHALL require the same valid edge credentials as other protected edge routes. Unauthenticated callers MUST NOT obtain Terminal secrets or create PaymentIntents. Terminal operations MUST be limited to organisations/events permitted by the edge credential binding (no foreign-event PaymentIntents).

#### Scenario: Terminal endpoint without edge credentials fails
- **WHEN** a client calls an edge Stripe Terminal endpoint without valid edge credentials
- **THEN** the response is HTTP 401 or 403
- **AND** no Terminal connection token or PaymentIntent is created

#### Scenario: Terminal PaymentIntent rejected for foreign event
- **WHEN** an authenticated edge client requests a Terminal PaymentIntent for an event outside its credential scope
- **THEN** the response is HTTP 404 or 403
- **AND** no PaymentIntent is created for that foreign event

### Requirement: Hosted-Pi manager requires a shared secret
Calls from cloud-backend to the hosted-Pi manager SHALL authenticate with `HOSTED_PI_MANAGER_SECRET` (or equivalent header). Requests without the correct secret MUST be rejected. Provision responses that include edge credentials MUST only be returned on the authenticated manager channel, not to anonymous callers.

#### Scenario: Manager rejects missing secret
- **WHEN** a client calls a hosted-Pi manager provision or destroy endpoint without a valid manager secret
- **THEN** the response is HTTP 401
- **AND** no instance is provisioned or destroyed
