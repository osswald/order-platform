## ADDED Requirements

### Requirement: Failed or cancelled connected checkout leaves order unpaid
When a SumUp connected (`sumup_connected`) checkout ends as failed, terminated, cancelled, or timed out without a successful confirmed payment, the system SHALL NOT record an order payment for that attempt and SHALL leave the order payment status unpaid/open for the affected amounts. A subsequent successful payment attempt (same or different method) MUST still be allowed.

#### Scenario: Failed checkout does not pay the order
- **WHEN** a SumUp reader checkout reaches a failed or terminated status before the POS records payment
- **THEN** no `sumup_connected` payment is stored on the order for that attempt and the order remains open for the unsettled amount

#### Scenario: Retry after failure
- **WHEN** a previous SumUp connected attempt failed or was terminated and the order is still open
- **THEN** the POS may create a new checkout or record a different payment method for the remaining amount

### Requirement: POS can terminate an in-progress connected checkout
While a SumUp connected checkout is awaiting cardholder action, the Pi POS SHALL provide an operator action that invokes the existing edge terminate capability for the active reader. Terminate MUST be reachable from the waiting UI without requiring the operator to abandon the device or wait for timeout.

#### Scenario: Operator terminate from waiting UI
- **WHEN** the POS cancels an in-progress SumUp connected payment from the waiting UI
- **THEN** the cloud requests SumUp terminate for that reader and the order is not marked paid for that attempt
