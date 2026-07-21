# cloud-event-save Specification

## Purpose

Cloud event detail save behavior: status-only persistence on confirmed lifecycle transitions, staying on the event after create/edit stammdaten save, and stable debounced autosave for configuration and related silos.

## Requirements

### Requirement: Confirmed status transition persists status only

When an operator confirms an allowed event status transition in the cloud event detail status stepper, the system SHALL persist only the new `status` to the server and SHALL NOT include other stammdaten fields in that request. The system SHALL keep the operator on the event detail after success. On failure, the system SHALL leave the event on the previous server status and SHALL surface an error.

#### Scenario: Successful status transition stays on detail

- **WHEN** the operator confirms a valid next status (for example test → prod) on an existing event
- **THEN** the client sends a status-only update for that event
- **AND** the UI reflects the new status as saved
- **AND** the operator remains on that event’s detail view

#### Scenario: Status transition does not commit other dirty stammdaten

- **WHEN** the operator has unsaved changes to non-status stammdaten fields (for example name or dates)
- **AND** the operator confirms a status transition
- **THEN** the status-only update succeeds without sending those other field values
- **AND** the non-status stammdaten fields remain unsaved (dirty) until the operator saves them separately

#### Scenario: Failed status transition does not advance UI

- **WHEN** the operator confirms a status transition
- **AND** the status update fails
- **THEN** the stepper continues to show the previous status
- **AND** an error is shown to the operator

### Requirement: Create and edit stammdaten save stay on event detail

After a successful create or edit save of event stammdaten from the cloud event detail form, the system SHALL keep the operator on the event detail (for create, the newly created event’s detail). The system SHALL NOT navigate to the event list solely because that save succeeded.

#### Scenario: Edit save remains on detail

- **WHEN** the operator saves stammdaten changes on an existing event successfully
- **THEN** the operator remains on that event’s detail view

#### Scenario: Create save opens new event detail

- **WHEN** the operator creates an event successfully
- **THEN** the client navigates to the new event’s detail view
- **AND** does not navigate to the event list as the primary post-create destination

### Requirement: Debounced autosave resumes when re-enabled while dirty

The shared dirty autosave mechanism used by event configuration (and other silos) SHALL schedule a save when autosave becomes enabled again while the silo is dirty. Temporary disable gates (loading, open layout cell dialog, layout cells loading) MUST NOT leave a permanently stuck dirty state that never saves without a further unrelated edit.

#### Scenario: Autosave resumes after disable gate clears

- **WHEN** configuration (or another autosave silo) is dirty
- **AND** autosave is temporarily disabled by a gate
- **AND** the gate clears so autosave is enabled again
- **THEN** a save is scheduled (or run) without requiring an additional user edit

#### Scenario: Debounce still coalesces rapid edits when enabled

- **WHEN** autosave is enabled and the operator makes rapid successive edits
- **THEN** the silo continues to debounce and coalesce saves as before
- **AND** a successful save leaves the silo in a saved state when the snapshot matches the server baseline
