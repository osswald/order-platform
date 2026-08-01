## REMOVED Requirements

### Requirement: Android bridge reports Tap to Pay device support
**Reason**: Phone Tap to Pay via Stripe Terminal is removed; card present uses SumUp Solo Cloud API.
**Migration**: Remove `AndroidTerminal.supportsTapToPay` / Stripe Terminal SDK usage; gate `sumup_connected` on org connection, paired readers, and cloud reachability instead.

### Requirement: Payment picker disables Karte on unsupported devices
**Reason**: Karte/`stripe_terminal` Tap to Pay picker gating is obsolete.
**Migration**: Payment picker offers Sumup connected when the event allows it and a session/register reader is available; no Android Tap to Pay support check.

### Requirement: Support check uses simulated discovery in debug builds
**Reason**: Stripe Terminal simulated Tap to Pay discovery is removed with the SDK.
**Migration**: Use SumUp Virtual Solo / sandbox merchants for Cloud API testing.

### Requirement: Bridge returns structured Tap to Pay eligibility checks
**Reason**: Stripe Tap to Pay eligibility checklist is removed with Terminal.
**Migration**: None for POS; optional future Solo online-status hints are out of scope for this change’s Android bridge.

### Requirement: Terminal init uses locale configuration
**Reason**: Stripe Terminal SDK initialization is removed.
**Migration**: Delete Terminal init paths from the Android app.
