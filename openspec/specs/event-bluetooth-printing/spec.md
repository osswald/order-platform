# event-bluetooth-printing Specification

## Purpose
Per-event Stammdaten switch that enables Bluetooth printing on paired Pi waiter devices, including edge-bundle sync and waiter-hub UI gating.
## Requirements
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

On Android waiter devices, the Pi PWA SHALL use a configured Bluetooth printer for payment receipts, voucher slips, and shift settlement receipts only when the selected event has `bluetooth_printing_enabled` true **and** the selected Bluetooth printer is reachable. When the flag is false, the PWA SHALL fall back to network printer selection even if a Bluetooth printer is paired. When the flag is true but the selected printer is not reachable (or Bluetooth print fails), the PWA SHALL fall back to network/station printer selection when targets exist, instead of stopping after a Bluetooth-only failure.

#### Scenario: Flag off with paired printer

- **WHEN** a waiter completes a flow that can print via Bluetooth and the event has `bluetooth_printing_enabled` false
- **THEN** the app does not send ESC/POS over Bluetooth and uses network printers (or reports no printer) instead

#### Scenario: Flag on with paired printer

- **WHEN** the event has `bluetooth_printing_enabled` true, a Bluetooth printer is configured on the Android device, and the selected printer answers a reachability check
- **THEN** the app prints those payloads via Bluetooth without requiring a station picker

#### Scenario: Flag on with unreachable paired printer

- **WHEN** the event has `bluetooth_printing_enabled` true, a Bluetooth printer is configured, the waiter wants a payment receipt, and the selected printer does not answer a reachability check
- **THEN** the app does not treat Bluetooth as ready, informs the waiter that the Bluetooth printer is unavailable, and offers network/station printer selection when targets exist

#### Scenario: Bluetooth print fails after probe

- **WHEN** a reachability check succeeded (or an older APK without the probe attempted Bluetooth) and the subsequent Bluetooth print fails, and network printer targets exist
- **THEN** the app SHALL fall back to network/station printer selection rather than ending only with a Bluetooth error

### Requirement: Waiter hub Bluetooth tile respects event flag

The waiter hub SHALL show the «Bluetooth Drucker» setup action only on Android when the selected event has Bluetooth printing enabled. The admin hub MAY continue to offer Bluetooth printer setup on Android regardless of event.

#### Scenario: Waiter hub hidden when disabled

- **WHEN** a waiter is on Android for an event with `bluetooth_printing_enabled` false
- **THEN** the waiter hub does not show the Bluetooth printer setup button

### Requirement: Settlement completion is independent of receipt printing

After a payment has been successfully committed, the Pi PWA SHALL complete the settle UI flow (fully settled: leave split-pay / navigate as today; partial settle: refresh and remain for further payment) even when payment-receipt prompting or printing fails, times out, or is cancelled after the ask step. Receipt errors MAY be toasted and MAY offer station fallback, but MUST NOT prevent `settled` emission or post-pay navigation.

#### Scenario: Bluetooth print fails after full table settle

- **WHEN** a waiter fully settles an open table/account and confirms a payment receipt, and Bluetooth printing fails (printer missing / unreachable / error)
- **THEN** the payment remains settled and the UI leaves the split-pay screen (or otherwise completes the settled flow) instead of remaining on the settle screen as if payment failed

#### Scenario: Receipt failure after full-order pay

- **WHEN** a waiter pays an open order successfully and receipt printing fails
- **THEN** the app still navigates away from the pay screen as it does after a successful pay without printing

### Requirement: Android bridge exposes selected-printer reachability

The Android waiter app SHALL expose a Javascript bridge method on `AndroidPrinter` that checks whether the currently selected Classic Bluetooth ESC/POS printer can accept an RFCOMM connection, without printing a receipt payload. The check SHALL reuse the same device address and SPP UUID as `printEscposBase64`, SHALL apply a short connect timeout, and SHALL return JSON indicating success or failure.

#### Scenario: Selected printer in range

- **WHEN** the PWA calls the reachability method and the selected bonded printer accepts an RFCOMM connect within the timeout
- **THEN** the bridge returns `{ "ok": true }` (and MAY include the printer address)

#### Scenario: Selected printer offline or out of range

- **WHEN** the PWA calls the reachability method and connect fails or times out
- **THEN** the bridge returns `{ "ok": false, "error": "…" }` and does not claim the printer is ready

#### Scenario: No printer selected or permission missing

- **WHEN** no address is selected, Bluetooth permission is missing, or no adapter is available
- **THEN** the bridge returns `{ "ok": false, "error": "…" }` without hanging indefinitely

