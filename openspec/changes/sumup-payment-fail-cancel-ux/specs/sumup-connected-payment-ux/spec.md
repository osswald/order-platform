## Purpose

Define Pi POS operator UX for in-progress SumUp connected (`sumup_connected`) payments: waiting UI with cancel, prominent failure messaging, return to settle for retry or another method, and attempt-scoped guards so failed or cancelled attempts never settle the order and concurrent green-check taps cannot leave split-pay with nothing to settle.

## ADDED Requirements

### Requirement: Waiting UI exposes cancel for SumUp connected
While the Pi POS is awaiting cardholder action for a `sumup_connected` checkout, the shared waiting UI SHALL show an operator-visible cancel control. Activating cancel MUST request SumUp terminate for the active reader (best effort), MUST end the waiting UI, MUST NOT record a payment for that attempt, and MUST leave the order (or open settle selection) unpaid so another payment method or a new SumUp attempt can be started. Cancel MUST be available from every POS entry point that can start `sumup_connected` (register settle, table settle, collective-bill settle, and legacy order pay).

#### Scenario: Operator cancels while reader waits
- **WHEN** the POS is showing the SumUp connected waiting UI and the operator activates cancel
- **THEN** the cloud/edge terminate path is invoked for that reader, the waiting UI closes, no payment is recorded for that attempt, and the operator returns to the settle or pay screen with the bill still open

#### Scenario: Cancel is quiet (not treated as hard failure)
- **WHEN** the operator cancels an in-progress SumUp connected payment
- **THEN** the POS does not show the failure sheet used for declines/timeouts and does not toast a payment-failure error for that cancel

### Requirement: Failed SumUp connected attempt shows a prominent on-screen message
When a `sumup_connected` collection ends in failure (card decline, SumUp `failed` / equivalent terminal failure, or collection timeout) without a successful settlement, the Pi POS SHALL show a full-screen or sheet-level message that is larger and more persistent than a toast alone. The message MUST make clear that payment did not succeed. Dismissing the message MUST return the operator to the settle or pay screen with the order still unpaid so they can start pay again and choose the same or a different payment method. The POS MUST NOT auto-restart a new SumUp checkout solely because the failure sheet was dismissed.

#### Scenario: Decline or SumUp failure
- **WHEN** SumUp reports the checkout as failed (or equivalent) while the POS is collecting `sumup_connected`
- **THEN** the waiting UI ends, a prominent failure message is shown, and after dismiss the operator is on the settle or pay screen with no payment recorded for that attempt

#### Scenario: Collection timeout
- **WHEN** SumUp connected polling exceeds the collection timeout without a successful paid status
- **THEN** the POS best-effort terminates the reader checkout, shows the prominent failure message, and leaves the order unpaid

#### Scenario: Dismiss returns to settle without auto-restart
- **WHEN** the operator dismisses the SumUp connected failure message
- **THEN** the POS returns to the settle or pay screen and does not immediately create a new SumUp checkout until the operator starts pay again

### Requirement: Pay action locked for the whole SumUp collection window
From the moment a `sumup_connected` collection starts until it finishes (success, failure, timeout, or operator cancel), the Pi POS SHALL prevent a second concurrent payment collection or settle for that same settle/pay context. The lock MUST cover the entire reader wait, not only the final settle HTTP call after SumUp succeeds.

#### Scenario: Double green-check during wait is ignored
- **WHEN** a SumUp connected wait is already in progress for a settle screen and the operator activates pay again
- **THEN** the POS does not start a second checkout or settle and the open line selection remains unchanged

#### Scenario: After failure, a new pay is allowed
- **WHEN** a previous SumUp connected attempt has fully ended in failure or cancel and the failure/cancel UI is dismissed
- **THEN** the operator can start a new payment attempt (including a different method) without needing to leave and re-enter the settle screen solely because of the failed attempt

### Requirement: Cancelled or failed attempts never settle that attempt
The Pi POS MUST NOT call settle/pay with a `sumup_connected` payment for an attempt that the operator cancelled or that ended in failure/timeout. If SumUp later reports paid for a checkout that belongs to a cancelled local attempt, the POS MUST NOT automatically settle that payment into the order as part of the cancelled attempt.

#### Scenario: Late paid after cancel is not auto-settled
- **WHEN** the operator has cancelled a SumUp connected attempt and SumUp later reports that checkout as paid
- **THEN** the cancelled attempt’s flow does not settle the order as a successful completion of that attempt

#### Scenario: Failed collection does not call settle
- **WHEN** SumUp connected collection throws or returns a non-success terminal status
- **THEN** the POS does not POST settle-partial or pay for that attempt and open amounts remain unpaid
