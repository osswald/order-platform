## REMOVED Requirements

### Requirement: Native bridge exposes a non-charging Tap to Pay readiness check
**Reason**: Pi Admin Tap to Pay readiness was for Stripe Terminal on the phone; product uses Solo Cloud API instead.
**Migration**: Remove the native readiness bridge method and any PaymentIntent-free Terminal capability checks.

### Requirement: Pi Admin runs the Tap to Pay readiness check on load
**Reason**: Admin Tap to Pay check is retired.
**Migration**: Remove Admin-load trigger for Tap to Pay readiness.

### Requirement: Pi Admin displays Tap to Pay readiness status
**Reason**: Admin Tap to Pay status UI is retired.
**Migration**: Remove Tap to Pay status line from Pi Admin hub.

### Requirement: Pi Admin lists Tap to Pay eligibility checks when not ready
**Reason**: Eligibility checklist UI is retired with Stripe Terminal.
**Migration**: Remove checklist rendering from Pi Admin hub.
