# pi-connection-setup Specification

## Purpose
Define first-run Pi API connection setup when the venue Pi is unreachable, including the Play review demo shortcut (Option B Play Store distribution).

## Requirements

### Requirement: Probe Pi connectivity on startup

The Pi frontend SHALL probe reachability of the current API base on startup before proceeding to setup/pairing or main app routes.

#### Scenario: Default LAN Pi reachable

- **WHEN** the app starts with default API base `http://192.168.192.10` and the venue Pi responds to the probe
- **THEN** the app SHALL continue to the normal startup flow (setup redirect if unpaired, otherwise main routes)

#### Scenario: Default LAN Pi unreachable

- **WHEN** the app starts and the probe to the current API base fails with a network error
- **THEN** the app SHALL navigate to the connection setup flow before other guards

### Requirement: Connection setup URL entry and test

The connection setup flow SHALL allow the user to enter a Pi API base URL, test connectivity, and persist the chosen base URL.

#### Scenario: Successful test and save

- **WHEN** the user enters a valid Pi API base URL and taps test connection
- **THEN** the app SHALL confirm reachability and enable save

- **WHEN** the user saves after a successful test
- **THEN** the app SHALL persist the URL via `setApiBase()` and continue startup against the new base

#### Scenario: Failed test

- **WHEN** the user tests an unreachable URL
- **THEN** the app SHALL show an error and SHALL NOT save until a successful test

### Requirement: Play review demo shortcut

The connection setup flow SHALL offer a one-tap action that sets the API base to `https://play-review.demo.vendiqo.ch`, tests connectivity, and saves on success.

#### Scenario: Review demo shortcut

- **WHEN** the user taps **Use Play review demo** (or equivalent label)
- **THEN** the app SHALL set the API base to `https://play-review.demo.vendiqo.ch`, run the connectivity test, and save on success

### Requirement: Persisted URL survives restarts

Once saved, the configured API base SHALL be used on subsequent app launches without repeating setup unless the probe fails again.

#### Scenario: Saved URL reused

- **WHEN** the user previously saved a custom API base and the Pi responds on next launch
- **THEN** the app SHALL use the saved base and SHALL NOT show connection setup

#### Scenario: Saved URL becomes unreachable

- **WHEN** the saved API base no longer responds on launch
- **THEN** the app SHALL show connection setup again with the last saved URL pre-filled

### Requirement: Admin can change API base after setup

The existing admin sync/settings surface SHALL continue to allow changing the Pi API base URL after initial connection setup.

#### Scenario: Admin updates API base

- **WHEN** an administrator changes the Pi API base URL in admin settings
- **THEN** subsequent API calls SHALL use the updated base URL
