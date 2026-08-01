# stripe-terminal-device-support Specification

## Purpose
Retired. Phone Tap to Pay via Stripe Terminal is removed; card-present payments use SumUp Solo Cloud API. See `sumup-cloud-payments` and `sumup-solo-readers`.

## Requirements

### Requirement: Stripe Terminal Tap to Pay device support is retired
The Android waiter app SHALL NOT expose Stripe Terminal Tap to Pay support checks (`AndroidTerminal.supportsTapToPay` or equivalent), simulated Terminal discovery for support checks, structured Tap to Pay eligibility checklists, or Stripe Terminal SDK initialization with locale configuration. Card-present availability SHALL be gated by SumUp organisation connection, paired readers, and cloud reachability instead (`sumup-cloud-payments`).

#### Scenario: No Tap to Pay support bridge
- **WHEN** the Pi PWA evaluates whether card-present payment is available on Android
- **THEN** it MUST NOT call a Stripe Terminal Tap to Pay device-support bridge
- **AND** `sumup_connected` availability depends on org connection, paired readers, and cloud reachability

#### Scenario: No Stripe Terminal SDK init path
- **WHEN** the Android waiter app starts
- **THEN** it MUST NOT initialize the Stripe Terminal SDK for Tap to Pay
