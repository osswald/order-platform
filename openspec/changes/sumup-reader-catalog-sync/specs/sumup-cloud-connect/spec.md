## ADDED Requirements

### Requirement: Connect imports merchant readers
When an organisation becomes SumUp-connected by submitting a valid API key, or when a connected organisation updates the API key for the **same** merchant, the cloud SHALL import that merchant’s Cloud API reader catalog into the organisation’s stored readers using the same catalog rules as listing (insert missing ids, refresh status, prune ids absent from a successful well-formed list). Connecting MUST NOT require the admin to re-pair readers that SumUp already lists for that merchant.

#### Scenario: Connect imports existing Solos
- **WHEN** an authorised user connects an organisation with a valid API key and SumUp lists one or more readers for the chosen merchant
- **THEN** those readers are stored for the organisation and SumUp-Geräte shows them without a further pairing step

#### Scenario: Same-merchant key update re-syncs catalog
- **WHEN** an authorised user updates the API key for a connected organisation and the key belongs to the same merchant
- **THEN** the stored credential is replaced and the merchant reader catalog is re-synced (import, status refresh, prune)

#### Scenario: Connect still succeeds when reader list fails
- **WHEN** API-key connect (or same-merchant update) succeeds but SumUp’s reader list cannot be fetched
- **THEN** the organisation remains connected and existing local readers are left unchanged
