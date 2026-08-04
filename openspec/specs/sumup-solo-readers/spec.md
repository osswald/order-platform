# sumup-solo-readers Specification

## Purpose
Organisation-merchant-scoped SumUp Solo reader pairing and management on SumUp-Geräte, with required human-readable labels used in POS device pickers.

## Requirements

### Requirement: Pair Solo reader with required label
For a SumUp-connected organisation, authorised users SHALL pair a Solo reader by submitting the device pairing code and a non-empty **label**. The cloud SHALL call SumUp Create Reader for that organisation’s `merchant_code` using the organisation’s OAuth access token, persist the returned `reader_id` with the label under the organisation, and use the label as the SumUp reader name.

#### Scenario: Successful pair
- **WHEN** an authorised user submits a valid pairing code and label for a connected organisation
- **THEN** the reader is stored under that organisation with the given label and SumUp `reader_id`

#### Scenario: Label required
- **WHEN** an authorised user attempts to pair without a non-empty label
- **THEN** the request is rejected without creating a SumUp reader

### Requirement: List and manage readers by label
SumUp-Geräte SHALL list the organisation’s paired readers showing labels (and pairing/status when known). Authorised users SHALL be able to update a reader’s label and unpair a reader (SumUp delete + local removal). Waiter and cash-register UIs that select a device MUST present these labels, not raw `reader_id` values.

When listing readers for a SumUp-connected organisation, the cloud SHALL refresh each reader’s pairing status from SumUp’s merchant reader list and persist updates (e.g. `processing` → `paired`). If SumUp is unreachable, the list SHALL still return the last locally stored statuses.

#### Scenario: Label rename
- **WHEN** an authorised user updates a reader label
- **THEN** subsequent device pickers for that organisation show the new label for that reader

#### Scenario: Unpair
- **WHEN** an authorised user unpairs a reader
- **THEN** the reader is removed from the organisation’s list and MUST NOT appear in POS device pickers

#### Scenario: Status refreshed on list
- **WHEN** an authorised user opens SumUp-Geräte (or otherwise lists readers) for a connected organisation and SumUp reports a newer pairing status for a stored reader
- **THEN** the API response and persisted reader status reflect SumUp’s current pairing status

#### Scenario: List still works when SumUp status sync fails
- **WHEN** SumUp’s reader list cannot be fetched while listing local readers
- **THEN** the organisation’s stored readers are still returned with their last known statuses

### Requirement: Readers are organisation-merchant scoped
A Solo reader pairing SHALL belong to exactly one organisation’s SumUp merchant at a time. The system MUST NOT treat SumUp readers as hire-company appliances that can charge for multiple organisations without re-pairing under each organisation’s merchant.

#### Scenario: List is org-scoped
- **WHEN** an authorised user lists SumUp readers
- **THEN** only readers paired under the active organisation’s merchant are returned
