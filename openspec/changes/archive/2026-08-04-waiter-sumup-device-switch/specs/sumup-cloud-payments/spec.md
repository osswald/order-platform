## MODIFIED Requirements

### Requirement: Waiter selects SumUp device at login
When waiter mode is used and the event allows `sumup_connected`, the waiter login flow SHALL let the waiter choose a SumUp device from the organisation’s reader labels (auto-select when exactly one reader exists). The selection SHALL persist for the waiter session and be used for subsequent Sumup connected payments until the waiter changes it at login or from the waiter hub.

#### Scenario: Login picker
- **WHEN** a waiter logs in for an event with `sumup_connected` and more than one org reader
- **THEN** login requires selecting a labelled SumUp device before continuing

#### Scenario: Single reader auto-select
- **WHEN** a waiter logs in and the organisation has exactly one paired reader
- **THEN** that reader is selected without requiring a manual pick

## ADDED Requirements

### Requirement: Waiter changes SumUp device from hub
When a waiter is logged in for an event that allows `sumup_connected` and more than one organisation reader is available, the waiter hub SHALL show the currently assigned SumUp device label and SHALL allow the waiter to select a different labelled reader. Changing the device MUST update the waiter session binding for subsequent Sumup connected payments without logging out, re-entering PIN, or ending the shift. Cash-register default reader binding is unchanged by this flow.

#### Scenario: Hub shows assigned device
- **WHEN** a logged-in waiter has a SumUp reader on their session and the event allows `sumup_connected`
- **THEN** the waiter hub displays that reader’s label

#### Scenario: Mid-shift device switch
- **WHEN** the waiter chooses a different labelled SumUp device from the hub
- **THEN** the waiter session stores the new reader id and label, the shift remains open, and the next Sumup connected payment uses the new reader

#### Scenario: Switch without re-auth
- **WHEN** the waiter changes SumUp device from the hub
- **THEN** the POS does not require PIN entry and does not navigate through waiter login
