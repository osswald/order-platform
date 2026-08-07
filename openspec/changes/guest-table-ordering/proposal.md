## Why

At busy table-service events, taking orders is a staff bottleneck while kitchen fulfillment and waiter settlement already work well on the Pi. Guests with phones can place prepaid rounds themselves if orders only reach the venue after payment, without replacing classic waiter table service.

## What Changes

- Add event-level **guest self-order at table** (off by default) with a dedicated **Guest menu** config section when enabled.
- Guests scan a table QR (mobile data → `order.vendiqo.ch`), browse a curated guest menu, pay in the cloud, then receive a stay-at-table confirmation.
- Paid guest orders are delivered to the Pi only via a **separate pull poller** (active only when the feature is on); stock is deducted on Pi apply.
- Multiple phones at the same table create **separate** prepaid orders; table number is routing only.
- Waiter ordering and open-tab settlement remain unchanged and can run in parallel on the same table.
- Guest cancel is allowed only before payment; after pay, exceptions are staff-side only.
- Guest catalog hides monitored articles below a configurable stock threshold (default 15); unmonitored articles always show.
- If the event Pi has not been seen by cloud for longer than a configurable duration (default 10 minutes), guest checkout shows a soft unavailable message and blocks pay until the Pi is online again.
- Print table QR sheets (table number centered in the QR) from the Guest menu tab.
- **Payment rail is deferred** — design leaves a provider-agnostic payment session boundary; no provider locked in this change.

## Capabilities

### New Capabilities

- `guest-table-ordering`: Public guest order runtime on `order.vendiqo.ch` — QR deep link, prepaid rounds, stay-at-table UX, cancel-before-pay, stock visibility rules, Pi-offline soft gate, and cloud inbox of paid orders awaiting Pi pull.
- `guest-menu-config`: Cloud admin event configuration for enabling self-order, building guest menu categories from station articles, configurable stock/offline thresholds, and table QR preview/print.
- `guest-order-edge-delivery`: Pi-side separate poller (feature-gated) that pulls paid guest orders from cloud, creates local paid orders with table routing, deducts stock, drives kitchen/print, and acks delivery.

### Modified Capabilities

- (none)

## Impact

- **Cloud backend**: Event self-order settings + guest menu models; public guest APIs; paid-order inbox; edge pull/ack endpoints; use `edge_credential.last_seen_at` for offline gate; OpenAPI export for admin types; CORS/`ALLOWED_ORIGINS` for `order.vendiqo.ch`.
- **Cloud frontend (admin)**: New Guest menu config section (conditional), QR print UX, feature toggle + thresholds on event.
- **New guest frontend**: Lightweight Vue app hosted at `order.vendiqo.ch` (separate from `admin.vendiqo.ch`).
- **Pi backend**: Feature-gated guest-order poller; apply paid guest orders into local order/kitchen/stock paths; waiter APIs unchanged.
- **Pi frontend**: Optional read-only visibility of recent guest/paid table activity (nice-to-have; not required for MVP).
- **Ops / DNS**: TLS and routing for `order.vendiqo.ch`; privacy copy update when shipping.
- **Payments**: Adapter boundary only; concrete SumUp/TWINT/Stripe (etc.) chosen in a follow-up.
- **Deps**: QR generate/print libraries for admin; guest app tooling aligned with Node 24.
