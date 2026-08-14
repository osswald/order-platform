# sumup-cloud-connect Specification

## Purpose
Organisation-scoped SumUp API-key connect (primary), disconnect, and account status via the SumUp-Geräte admin surface. Dormant OAuth authorize/callback may remain mounted for future use but MUST NOT be the admin connect path while API-key connect is primary.

## Requirements

### Requirement: Organisation connects SumUp via API key
The cloud backend SHALL allow organisation managers (organisation admin for that organisation, tenant admin, or platform/superuser) to connect SumUp for the active organisation by submitting a SumUp merchant API key. The backend MUST validate the key against SumUp, persist the merchant identity and credential on that organisation, and MUST NOT return the API key in any subsequent API response. API-key paste SHALL be the primary connect path. The platform MAY retain dormant SumUp OAuth authorize and callback endpoints for future use, but the SumUp-Geräte UI MUST NOT present OAuth as the connect path while API-key connect is primary.

#### Scenario: Connect with API key
- **WHEN** an authorised user submits a valid SumUp merchant API key for an organisation that is not yet linked
- **THEN** the system validates the key with SumUp, persists `merchant_code` and the credential for that organisation, and marks the organisation as SumUp-connected

#### Scenario: Invalid API key rejected
- **WHEN** an authorised user submits an empty or SumUp-rejected API key
- **THEN** the organisation remains unconnected and the client receives an error without storing the credential

#### Scenario: Credential never echoed
- **WHEN** an authorised user reads SumUp connection status after a successful API-key connect
- **THEN** the response includes connection state and merchant identity but does not include the API key value

### Requirement: SumUp-Geräte is the connect and account surface
The cloud admin UI SHALL expose a Hauptmenü item **SumUp-Geräte** visible to organisation admins, tenant admins, and platform/superusers, scoped to the active organisation. When the organisation is not SumUp-connected, that page SHALL present API-key paste connect (with brief guidance that the key is created in the SumUp merchant developer settings) and MUST NOT present an OAuth connect call-to-action. When connected, it SHALL show account/connection status, allow updating the API key without wiping paired readers when the new key belongs to the same merchant, and allow disconnect (clearing stored credentials and connection state and local reader rows without deleting historical payment records). When the platform Affiliate Key required for Solo checkout is missing, the page SHOULD show that card payments are not ready on this server without blocking API-key connect.

#### Scenario: Unconnected organisation sees API key connect
- **WHEN** an authorised user opens SumUp-Geräte for an organisation with no SumUp connection
- **THEN** the page offers SumUp API-key connect and does not offer OAuth connect or reader pairing

#### Scenario: Connected organisation can update API key
- **WHEN** an authorised user submits a new valid API key for a connected organisation whose SumUp merchant matches the existing `merchant_code`
- **THEN** the stored credential is replaced, paired readers remain, and the organisation stays connected

#### Scenario: API key update rejects different merchant
- **WHEN** an authorised user submits an API key whose SumUp merchant differs from the organisation’s stored `merchant_code`
- **THEN** the update is rejected, the previous credential remains, and local readers are unchanged

#### Scenario: Connected organisation can disconnect
- **WHEN** an authorised user disconnects SumUp on SumUp-Geräte
- **THEN** stored credentials and merchant linkage for that organisation are cleared, local reader rows are removed, and reader management actions that require SumUp API access are unavailable until reconnect

### Requirement: Organisation SumUp credential resolves for Cloud API calls
For a SumUp-connected organisation, cloud services that call SumUp (reader management and edge Solo checkout) SHALL obtain a Bearer credential from the organisation’s stored SumUp credential. When a refresh token is present, the system MAY refresh an OAuth access token as before. When no refresh token is present, the system SHALL use the stored access credential as a static API key without attempting token refresh. API-key connect MUST NOT require platform OAuth client environment variables to be configured.

#### Scenario: API-key organisation authorizes SumUp calls
- **WHEN** a connected organisation has a stored SumUp credential and no refresh token
- **THEN** reader and checkout calls to SumUp use that credential as the Bearer token and do not attempt OAuth refresh

#### Scenario: Connect without OAuth client env
- **WHEN** platform OAuth client id/secret/redirect are unset and an authorised user connects with a valid API key
- **THEN** the organisation becomes SumUp-connected successfully

### Requirement: Access control matches organisation management
SumUp connect, disconnect, and credential APIs SHALL authorize with the same organisation-management rule as other org-scoped admin actions: platform/superuser and tenant admin for tenant orgs, or organisation admin only for organisations they administer. Members without those roles MUST NOT access SumUp connect or reader management APIs.

#### Scenario: Member denied
- **WHEN** a member without organisation-admin rights calls a SumUp connect or reader management endpoint
- **THEN** the request is rejected as forbidden
