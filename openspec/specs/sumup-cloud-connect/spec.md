# sumup-cloud-connect Specification

## Purpose
Organisation-scoped SumUp OAuth connect, disconnect, and account status via the SumUp-Geräte admin surface (no API-key paste as the primary path).

## Requirements

### Requirement: Organisation connects SumUp via OAuth
The cloud backend SHALL allow organisation managers (organisation admin for that organisation, tenant admin, or platform/superuser) to start a SumUp OAuth authorization-code flow for the active organisation and persist the resulting merchant identity and refreshable tokens on that organisation. API-key paste SHALL NOT be offered as the primary connect path.

#### Scenario: Connect starts OAuth
- **WHEN** an authorised user starts SumUp connect for an organisation that is not yet linked
- **THEN** the system redirects or returns a SumUp authorize URL for the platform OAuth app with a verifiable `state` bound to that organisation

#### Scenario: Callback stores merchant credentials
- **WHEN** SumUp redirects back with a valid authorization code and matching `state`
- **THEN** the backend exchanges the code for tokens, persists `merchant_code` and tokens for that organisation, and marks the organisation as SumUp-connected

### Requirement: SumUp-Geräte is the connect and account surface
The cloud admin UI SHALL expose a Hauptmenü item **SumUp-Geräte** visible to organisation admins, tenant admins, and platform/superusers, scoped to the active organisation. When the organisation is not SumUp-connected, that page SHALL present the OAuth connect call-to-action and explanation. When connected, it SHALL show account/connection status and allow disconnect (revoking stored tokens and clearing connection state without deleting historical payment records).

#### Scenario: Unconnected organisation sees connect CTA
- **WHEN** an authorised user opens SumUp-Geräte for an organisation with no SumUp connection
- **THEN** the page offers SumUp OAuth connect and does not offer reader pairing

#### Scenario: Connected organisation can disconnect
- **WHEN** an authorised user disconnects SumUp on SumUp-Geräte
- **THEN** stored OAuth tokens and merchant linkage for that organisation are cleared and reader management actions that require SumUp API access are unavailable until reconnect

### Requirement: Access control matches organisation management
SumUp connect, disconnect, and credential APIs SHALL authorize with the same organisation-management rule as other org-scoped admin actions: platform/superuser and tenant admin for tenant orgs, or organisation admin only for organisations they administer. Members without those roles MUST NOT access SumUp connect or reader management APIs.

#### Scenario: Member denied
- **WHEN** a member without organisation-admin rights calls a SumUp connect or reader management endpoint
- **THEN** the request is rejected as forbidden
