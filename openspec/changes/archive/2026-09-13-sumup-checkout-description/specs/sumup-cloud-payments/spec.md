## ADDED Requirements

### Requirement: Merchant Sales checkout description
When the cloud creates a SumUp Solo reader checkout for `sumup_connected`, it SHALL set SumUp’s checkout `description` to a human-readable label for Merchant Sales. The description MUST be the non-empty parts of **event name**, **Solo reader label**, and **waiter name**, joined in that order. The Solo label MUST be the organisation’s stored reader label for the checkout’s `reader_id`, not a cash-register name. Waiter name MUST be included when the POS supplies a waiter identity for that checkout and that waiter belongs to the event; otherwise the waiter part MUST be omitted. The system MUST NOT use `Event {id}` as the description. The system MUST omit empty parts rather than insert placeholders. The joined description MUST be truncated to at most 90 characters so it remains usable in SumUp Merchant Sales.

#### Scenario: Waiter payment includes event, Solo, and waiter
- **WHEN** a waiter completes Sumup connected pay on a labelled Solo
- **THEN** the SumUp checkout description is `{event name} · {Solo label} · {waiter name}` (truncated to 90 characters if needed)

#### Scenario: Register payment omits waiter
- **WHEN** a cash-register Sumup connected pay is created with no waiter identity
- **THEN** the SumUp checkout description is `{event name} · {Solo label}` and does not include a waiter name

#### Scenario: Missing parts are skipped
- **WHEN** the waiter identity is absent or does not match an event waiter
- **THEN** the description is built from the remaining known parts only and does not contain `Event {id}` or empty placeholder slots

#### Scenario: Description length cap
- **WHEN** the joined event name, Solo label, and waiter name exceed 90 characters
- **THEN** the value sent to SumUp is at most 90 characters
