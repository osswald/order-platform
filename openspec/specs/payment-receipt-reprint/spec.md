# payment-receipt-reprint Specification

## Purpose

Ensures payment receipt reprints are visibly marked on both Bluetooth and network printers so staff can distinguish copies from original Zahlungsbelege.

## Requirements

### Requirement: Payment receipt reprints include a reprint marker

When a payment receipt is printed as a reprint (client sets `reprint` true), the rendered ESC/POS payload MUST include the line «Kopie / Nachdruck» after the «Beleg» header. This MUST apply to both the immediate ESC/POS receipt endpoint and network station print jobs. When `reprint` is false or omitted, the payload MUST NOT include that reprint marker.

#### Scenario: Bluetooth reprint includes marker

- **WHEN** a client requests ESC/POS for a payment receipt with `reprint: true`
- **THEN** the payload contains «Kopie / Nachdruck» after «Beleg»

#### Scenario: Network reprint includes marker

- **WHEN** a client enqueues a payment-receipt print to a station with `reprint: true`
- **THEN** the worker-built ESC/POS payload contains «Kopie / Nachdruck» after «Beleg»

#### Scenario: First print has no marker

- **WHEN** a client prints or enqueues a payment receipt without `reprint` (or with `reprint: false`)
- **THEN** the payload does not contain «Kopie / Nachdruck»

### Requirement: Belege reprint forwards reprint on network path

When the Pi PWA reprints a payment from Belege / receipt history and printing goes to a network station (directly or after Bluetooth fallback), the client MUST send `reprint: true` on the station print request.

#### Scenario: History reprint via station printer

- **WHEN** a waiter chooses Nachdrucken on Belege and printing uses a network/station target
- **THEN** the print request includes `reprint: true` and the printed slip shows «Kopie / Nachdruck»
