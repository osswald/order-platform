## ADDED Requirements

### Requirement: Failed SumUp connected settle attempt keeps open positions
On the shared Pi split-pay settle screen (register order settle, waiter table settle, and collective-bill settle), when a `sumup_connected` payment attempt fails, times out, or is cancelled by the operator before settle succeeds, the screen SHALL keep the current open positions and selection available for another payment attempt. The POS MUST NOT present an empty “nothing to settle” / no-open-items outcome solely because that SumUp attempt failed or was cancelled, and MUST NOT clear the settle context as if the bill were fully paid.

#### Scenario: After SumUp failure, settle screen still has open items
- **WHEN** the operator runs SumUp connected from split-pay and collection fails or is cancelled without a successful settle
- **THEN** the settle screen still shows the open positions (and prior selection where applicable) so pay can be started again

#### Scenario: Concurrent SumUp collection does not empty settle after a reported failure
- **WHEN** a SumUp connected wait is already in progress from split-pay
- **THEN** a second concurrent pay activation for that same settle context does not start another collection that can settle the bill while the first attempt is still reported as failed to the operator
