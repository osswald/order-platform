## Purpose

Detect when the venue Pi becomes unreachable after login (idle Android tablets, WiFi sleep) and recover softly — banner plus gated money-path actions — without forcing connection-setup or clearing the register/waiter session.

## ADDED Requirements

### Requirement: Track mid-session Pi reachability

The Pi frontend SHALL maintain a mid-session reachability status for the configured Pi API base, updated by probing the existing health endpoint (same probe mechanism as startup: fail-fast client timeout; Android native bridge when available).

#### Scenario: Successful probe marks reachable

- **WHEN** a mid-session health probe succeeds
- **THEN** the app SHALL mark the Pi as reachable and record the success time

#### Scenario: Failed probe marks unreachable

- **WHEN** a mid-session health probe fails with a network or non-OK HTTP result
- **THEN** the app SHALL mark the Pi as unreachable

### Requirement: Probe on resume when the app becomes visible

While a register or waiter session is active (or whenever the main app shell is running after startup), the Pi frontend SHALL probe Pi reachability when the document becomes visible again after being hidden.

#### Scenario: Tablet wakes after idle

- **WHEN** the document visibility changes from hidden to visible
- **THEN** the app SHALL run a Pi health probe and update reachability status from the result

### Requirement: Keepalive probe while visible

While the document is visible, the Pi frontend SHALL probe Pi reachability on a ~30 second interval. Probing SHALL stop while the document is hidden.

#### Scenario: Periodic check on hub

- **WHEN** the app remains visible for at least one keepalive interval
- **THEN** the app SHALL probe Pi health about every 30 seconds and update reachability status

#### Scenario: No keepalive while hidden

- **WHEN** the document is hidden
- **THEN** the app SHALL NOT continue the mid-session keepalive probe timer

### Requirement: Soft unreachable banner

When the Pi is marked unreachable mid-session, the register and waiter hub surfaces SHALL show a soft banner that does not clear the session and does not automatically navigate to connection setup. The banner SHALL offer a retry action that re-probes and an optional action to open connection setup so the operator can change the API base.

#### Scenario: Banner appears when unreachable

- **WHEN** mid-session reachability becomes unreachable while the operator is on the register or waiter hub
- **THEN** the hub SHALL show an unreachable banner
- **AND** the register or waiter session SHALL remain intact
- **AND** the app SHALL NOT automatically navigate to connection setup

#### Scenario: Retry clears banner after recovery

- **WHEN** the operator uses the banner retry action and the probe succeeds
- **THEN** the app SHALL mark the Pi as reachable and hide the unreachable banner

#### Scenario: Operator opens connection setup from banner

- **WHEN** the operator chooses the banner action to change the connection
- **THEN** the app SHALL navigate to the connection setup flow

### Requirement: Gate money-path actions until Pi is reachable

Register and waiter money-path actions SHALL NOT navigate into their flows while the Pi is unreachable. Before navigating, the app SHALL ensure reachability (reusing a recent successful probe within a short warm window, otherwise running a probe). While a probe for a gated action is in progress, the action SHALL NOT navigate. On probe failure, the app SHALL keep the operator on the current hub and show or keep the unreachable banner.

Gated register actions include: start new order, open collective bills, and resume an open unpaid order.

Gated waiter actions include: start new order, settle table, open tables list, collective bills, and stock.

#### Scenario: Recent successful probe allows immediate navigation

- **WHEN** the operator taps a gated money-path action
- **AND** the Pi was marked reachable by a successful probe within the warm window
- **THEN** the app SHALL navigate without waiting for a new probe

#### Scenario: Stale or unknown status probes before navigate

- **WHEN** the operator taps a gated money-path action
- **AND** there is no successful probe within the warm window
- **THEN** the app SHALL probe Pi health before navigating
- **AND** on success the app SHALL navigate to the action’s destination
- **AND** on failure the app SHALL NOT navigate and SHALL show the unreachable banner

#### Scenario: Unreachable blocks new order

- **WHEN** the Pi is marked unreachable
- **AND** the operator taps Neue Bestellung on the register or waiter hub
- **THEN** the app SHALL NOT navigate into the new-order flow

#### Scenario: Unreachable blocks settle and related waiter paths

- **WHEN** the Pi is marked unreachable
- **AND** the operator taps Tisch abrechnen, Offene Tische, Sammelrechnungen, or Lagerbestand on the waiter hub
- **THEN** the app SHALL NOT navigate into that flow

#### Scenario: Unreachable blocks register collective bills and resume

- **WHEN** the Pi is marked unreachable
- **AND** the operator taps Sammelrechnungen or an open unpaid order on the register hub
- **THEN** the app SHALL NOT navigate into that flow

### Requirement: Startup connection-setup behavior unchanged

Cold-start probing and automatic navigation to connection setup when the Pi is unreachable at launch SHALL continue to behave as specified by `pi-connection-setup`. Mid-session soft recovery SHALL NOT replace that startup path.

#### Scenario: Cold start still redirects when unreachable

- **WHEN** the app starts and the startup probe fails
- **THEN** the app SHALL navigate to connection setup as before
- **AND** mid-session soft-banner rules SHALL NOT apply to that startup failure
