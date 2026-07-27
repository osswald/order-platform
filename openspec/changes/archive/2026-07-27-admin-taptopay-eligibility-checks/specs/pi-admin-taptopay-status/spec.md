## ADDED Requirements

### Requirement: Pi Admin lists Tap to Pay eligibility checks when not ready

When Tap to Pay readiness is not fully OK on Android, the Pi Admin hub SHALL list every eligibility check returned by the native bridge and indicate which passed and which failed. The list SHALL NOT be shown when the device is ready (including ready-simulated).

#### Scenario: Checklist shown when unsupported

- **WHEN** an administrator opens the Pi Admin hub inside the Android wrapper
- **AND** the readiness result includes at least one failed eligibility check (or an overall not-ready status with a checks list)
- **THEN** the UI SHALL show the Tap to Pay summary status
- **AND** it SHALL list each check with a clear pass or fail indication
- **AND** passed checks SHALL still appear in that list alongside failed ones

#### Scenario: Checklist hidden when ready

- **WHEN** the readiness check reports the device is ready or ready (simulated)
- **AND** no eligibility check failed
- **THEN** the UI SHALL show only the Tap to Pay summary status line
- **AND** it SHALL NOT render the eligibility checklist

#### Scenario: Older APK without checks array

- **WHEN** the bridge returns a readiness status without a `checks` array
- **THEN** the UI SHALL show the existing summary status only
- **AND** it SHALL NOT error or block Admin

#### Scenario: Status still hidden outside Android

- **WHEN** the Pi Admin hub is opened without the Android Tap to Pay bridge
- **THEN** the UI SHALL NOT show Tap to Pay readiness or an eligibility checklist
