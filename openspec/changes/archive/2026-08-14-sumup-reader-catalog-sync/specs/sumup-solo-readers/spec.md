## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Reader telemetry tooltip on SumUp-Geräte
SumUp-Geräte SHALL show a tooltip on each listed paired reader that includes persisted device identity (serial and model when known) and, when available, live Cloud API reader status: online/offline, battery level, connection type, firmware version, and last activity. Telemetry MUST be fetched on demand for that reader (not as part of catalog list). If live status cannot be retrieved, the tooltip SHALL still show persisted identity and indicate that telemetry is unavailable. Telemetry MUST NOT be required to list, pair, rename, or unpair readers.

#### Scenario: Tooltip shows live status
- **WHEN** an authorised user opens the tooltip for a listed reader and SumUp returns reader status
- **THEN** the tooltip shows serial/model when known plus online/offline, battery, connection type, firmware, and last activity

#### Scenario: Tooltip degrades without telemetry
- **WHEN** an authorised user opens the tooltip and SumUp reader status cannot be retrieved
- **THEN** the tooltip still shows persisted serial/model when known and indicates telemetry is unavailable, and the reader remains listed
