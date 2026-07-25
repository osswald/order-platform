# pi-admin-taptopay-status Specification

## Purpose
Native Tap to Pay device-readiness check (bridge contract + Admin-load trigger) and its status display in the Pi Admin hub.

## Requirements

### Requirement: Native bridge exposes a non-charging Tap to Pay readiness check

The native Android app SHALL expose a JavaScript bridge method that performs a Tap to Pay device-readiness check without creating a PaymentIntent or collecting a payment, and returns a structured result the PWA can display.

#### Scenario: Capability check on a supported device

- **WHEN** the PWA calls the native Tap to Pay readiness method on a device that meets Tap to Pay hardware and OS requirements and has location permission granted
- **THEN** the bridge SHALL initialise the Terminal SDK if needed and use the SDK capability check (e.g. `supportsReadersOfType`) without collecting a payment
- **AND** it SHALL return a structured result indicating the device is ready

#### Scenario: Location permission missing

- **WHEN** the PWA calls the readiness method on a capable device where location permission is not granted
- **THEN** the bridge SHALL return a structured result indicating that location permission is missing (distinct from an unsupported device)

#### Scenario: Unsupported device

- **WHEN** the PWA calls the readiness method on a device that does not meet Tap to Pay hardware/OS requirements
- **THEN** the bridge SHALL return a structured result indicating the device is not supported (mapping the SDK error), without throwing an unhandled error to the WebView

#### Scenario: Debug build uses simulated reader

- **WHEN** the readiness check runs in a debug build
- **THEN** the bridge SHALL use the simulated Tap to Pay configuration for the capability check
- **AND** the returned result SHALL distinguish the simulated outcome from a production-ready outcome

### Requirement: Pi Admin runs the Tap to Pay readiness check on load

The Pi Admin hub SHALL trigger the Tap to Pay readiness check when the Admin page loads (not at cold app startup) and SHALL re-run it each time the Admin page is opened.

#### Scenario: Check runs when Admin opens

- **WHEN** an administrator opens the Pi Admin hub inside the Android wrapper
- **THEN** the readiness check SHALL be invoked as part of loading the Admin page
- **AND** while the asynchronous result is pending the UI SHALL show a neutral "checking" state rather than a failure

#### Scenario: Re-check on reopening Admin

- **WHEN** an administrator leaves and reopens the Pi Admin hub after granting location permission
- **THEN** the readiness check SHALL run again and reflect the updated permission state

### Requirement: Pi Admin displays Tap to Pay readiness status

The Pi Admin hub SHALL display a Tap to Pay readiness status line, labelled as device readiness (not a payment guarantee), only when running inside the Android wrapper.

#### Scenario: Ready status shown

- **WHEN** the readiness check reports the device is ready
- **THEN** the UI SHALL show a Tap to Pay status indicating the device is ready

#### Scenario: Actionable status shown for missing permission

- **WHEN** the readiness check reports location permission is missing
- **THEN** the UI SHALL show a Tap to Pay status that indicates the location permission is required (distinct from an unsupported-device status)

#### Scenario: Unsupported or error status shown

- **WHEN** the readiness check reports the device is unsupported or the check errored
- **THEN** the UI SHALL show a corresponding Tap to Pay status
- **AND** it SHALL NOT block admin access

#### Scenario: Status hidden outside the Android app

- **WHEN** the Pi Admin hub is opened in a normal browser (no native Tap to Pay bridge)
- **THEN** the UI SHALL NOT show a Tap to Pay readiness status line
