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

When listing readers for a SumUp-connected organisation, the cloud SHALL treat SumUp’s merchant reader list as the catalog: import remote readers that are not stored locally, refresh pairing status for matching ids, persist known device identity (serial and model) when SumUp provides it, and **remove** local reader rows whose SumUp `reader_id` is absent from a successful list response. A reader that is not registered with SumUp MUST NOT remain in the organisation’s list or POS device pickers. If SumUp is unreachable or the list response is not well-formed, the list SHALL still return the last locally stored readers and MUST NOT prune.

On import of a new remote reader, the cloud SHALL set the Vendiqo label from SumUp’s reader `name` when that name is non-empty; otherwise it SHALL use the device serial if present, else a generic Solo label. On later syncs, an existing local label MUST NOT be overwritten by SumUp’s `name` (rename in Vendiqo remains the source of truth).

When a local reader is pruned, cash-register default bindings that used that SumUp `reader_id` SHALL be cleared.

#### Scenario: Label rename
- **WHEN** an authorised user updates a reader label
- **THEN** subsequent device pickers for that organisation show the new label for that reader

#### Scenario: Unpair
- **WHEN** an authorised user unpairs a reader
- **THEN** the reader is removed from the organisation’s list and MUST NOT appear in POS device pickers

#### Scenario: Status refreshed on list
- **WHEN** an authorised user opens SumUp-Geräte (or otherwise lists readers) for a connected organisation and SumUp reports a newer pairing status for a stored reader
- **THEN** the API response and persisted reader status reflect SumUp’s current pairing status

#### Scenario: Remote reader imported on list
- **WHEN** SumUp’s merchant reader list includes a `reader_id` that is not stored for the organisation
- **THEN** the cloud persists that reader with a label taken from SumUp’s `name` (or serial / generic Solo fallback) and it appears on SumUp-Geräte and in POS device pickers

#### Scenario: Existing label preserved on sync
- **WHEN** a stored reader is listed again and SumUp’s `name` differs from the Vendiqo label
- **THEN** the Vendiqo label is unchanged

#### Scenario: Reader absent from SumUp is pruned
- **WHEN** SumUp successfully returns a well-formed merchant reader list that does not include a stored `reader_id`
- **THEN** that local reader row is deleted, it does not appear in POS device pickers, and cash-register defaults that used that `reader_id` are cleared

#### Scenario: List still works when SumUp status sync fails
- **WHEN** SumUp’s reader list cannot be fetched or is not well-formed while listing local readers
- **THEN** the organisation’s stored readers are still returned with their last known statuses and no local readers are deleted

### Requirement: Reader telemetry tooltip on SumUp-Geräte
SumUp-Geräte SHALL show a tooltip on each listed paired reader that includes persisted device identity (serial and model when known) and, when available, live Cloud API reader status: online/offline, battery level, connection type, firmware version, and last activity. Last activity SHALL be shown with the cloud admin locale datetime format (not a raw ISO timestamp). Telemetry MUST be fetched on demand for that reader (not as part of catalog list). If live status cannot be retrieved, the tooltip SHALL still show persisted identity and indicate that telemetry is unavailable. Telemetry MUST NOT be required to list, pair, rename, or unpair readers.

#### Scenario: Tooltip shows live status
- **WHEN** an authorised user opens the tooltip for a listed reader and SumUp returns reader status
- **THEN** the tooltip shows serial/model when known plus online/offline, battery, connection type, firmware, and last activity formatted for the UI locale

#### Scenario: Last activity is localized
- **WHEN** the tooltip includes a last-activity timestamp from SumUp
- **THEN** the timestamp is rendered with the shared cloud datetime formatter for the current UI locale

#### Scenario: Tooltip degrades without telemetry
- **WHEN** an authorised user opens the tooltip and SumUp reader status cannot be retrieved
- **THEN** the tooltip still shows persisted serial/model when known and indicates telemetry is unavailable, and the reader remains listed

### Requirement: Readers are organisation-merchant scoped
A Solo reader pairing SHALL belong to exactly one organisation’s SumUp merchant at a time. The system MUST NOT treat SumUp readers as hire-company appliances that can charge for multiple organisations without re-pairing under each organisation’s merchant.

#### Scenario: List is org-scoped
- **WHEN** an authorised user lists SumUp readers
- **THEN** only readers paired under the active organisation’s merchant are returned
