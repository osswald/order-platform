## ADDED Requirements

### Requirement: Probe fails fast when Pi is unreachable

The Pi connectivity probe SHALL abort within a short client-side timeout (target about 2.5 seconds) when the API base does not respond, so the connection setup flow appears quickly instead of waiting for the platform TCP timeout.

#### Scenario: Unreachable default LAN Pi shows setup promptly

- **WHEN** the app starts with default API base `http://192.168.192.10` and no Pi answers within the probe timeout
- **THEN** the probe SHALL fail with a network-style result
- **AND** the app SHALL navigate to the connection setup flow without waiting for a long OS-level connection timeout

#### Scenario: Timed-out connection test

- **WHEN** the user tests a URL that does not respond within the probe timeout
- **THEN** the connection setup UI SHALL show an unreachable/error message and SHALL NOT enable save

## MODIFIED Requirements

### Requirement: Play review demo shortcut

The connection setup flow SHALL offer a one-tap action labeled **Demo** that sets the API base to `https://play-review.demo.vendiqo.ch` and runs the connectivity test.

#### Scenario: Review demo shortcut

- **WHEN** the user taps **Demo**
- **THEN** the app SHALL set the API base field to `https://play-review.demo.vendiqo.ch` and run the connectivity test
- **AND** on success the user SHALL be able to save and continue (same save gate as a manual test)
