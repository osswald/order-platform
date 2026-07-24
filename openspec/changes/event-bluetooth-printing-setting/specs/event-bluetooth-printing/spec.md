## ADDED Requirements

### Requirement: Event Stammdaten Bluetooth printing switch

The cloud admin UI SHALL expose a boolean Stammdaten setting `bluetooth_printing_enabled` on each event, placed next to the payment-receipt offer switch. The setting SHALL default to false for new events and SHALL be included in event create/update API payloads and responses.

#### Scenario: Operator enables Bluetooth printing

- **WHEN** an operator turns on «Bluetooth-Druck aktivieren» (or equivalent i18n label) and saves the event
- **THEN** the event stores `bluetooth_printing_enabled=true` and subsequent event reads return that value

#### Scenario: Default off

- **WHEN** a new event is created without setting the flag
- **THEN** `bluetooth_printing_enabled` is false

### Requirement: Edge bundle includes Bluetooth printing flag

The cloud edge bundle SHALL include `bluetooth_printing_enabled` on each event so paired Pi appliances receive the setting on sync. Event copy SHALL copy the flag from the source event.

#### Scenario: Bundle sync

- **WHEN** a Pi pulls `/edge/v1/bundle` for an event with Bluetooth printing enabled
- **THEN** the event entry in the bundle includes `bluetooth_printing_enabled: true`

### Requirement: Pi uses Bluetooth only when event flag is enabled

On Android waiter devices, the Pi PWA SHALL use a configured Bluetooth printer for payment receipts, voucher slips, and shift settlement receipts only when the selected event has `bluetooth_printing_enabled` true. When the flag is false, the PWA SHALL fall back to network printer selection even if a Bluetooth printer is paired.

#### Scenario: Flag off with paired printer

- **WHEN** a waiter completes a flow that can print via Bluetooth and the event has `bluetooth_printing_enabled` false
- **THEN** the app does not send ESC/POS over Bluetooth and uses network printers (or reports no printer) instead

#### Scenario: Flag on with paired printer

- **WHEN** the event has `bluetooth_printing_enabled` true and a Bluetooth printer is configured on the Android device
- **THEN** the app prefers Bluetooth for those print paths as it does today when paired

### Requirement: Waiter hub Bluetooth tile respects event flag

The waiter hub SHALL show the «Bluetooth Drucker» setup action only on Android when the selected event has Bluetooth printing enabled. The admin hub MAY continue to offer Bluetooth printer setup on Android regardless of event.

#### Scenario: Waiter hub hidden when disabled

- **WHEN** a waiter is on Android for an event with `bluetooth_printing_enabled` false
- **THEN** the waiter hub does not show the Bluetooth printer setup button
