# pi-admin-taptopay-status Specification

## Purpose
Retired. Pi Admin Tap to Pay readiness was for Stripe Terminal on the phone; card-present payments use SumUp Solo Cloud API instead.

## Requirements

### Requirement: Pi Admin Tap to Pay readiness is retired
The Pi Admin hub SHALL NOT trigger a native Tap to Pay readiness check on load, SHALL NOT display a Tap to Pay readiness status line, and SHALL NOT list Tap to Pay eligibility checks. The native Android app SHALL NOT expose a PaymentIntent-free Stripe Terminal Tap to Pay readiness bridge method for Admin.

#### Scenario: Admin hub has no Tap to Pay status
- **WHEN** an administrator opens the Pi Admin hub inside the Android wrapper
- **THEN** the UI does not show a Tap to Pay readiness status line or eligibility checklist
- **AND** Admin does not invoke a native Tap to Pay readiness bridge method
