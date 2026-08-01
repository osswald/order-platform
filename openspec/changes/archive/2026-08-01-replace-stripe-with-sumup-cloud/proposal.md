## Why

Vendiqo’s only automated card path today is Stripe Connect + Android Tap to Pay. The product direction is physical **SumUp Solo** readers driven by the **SumUp Cloud API**, with each organisation owning its own SumUp merchant. Stripe (and the 0.2% platform fee) should be removed entirely; the existing offline SumUp payment type stays as a manual fallback under a clearer label.

## What Changes

- **BREAKING:** Remove Stripe Connect, Terminal, webhooks, Android Terminal SDK / Tap to Pay, edge Terminal APIs, org `stripe_*` columns, platform application fee, and Stripe-related docs/help/specs.
- Add organisation-scoped **SumUp OAuth** connection (day one; no API-key paste MVP).
- Add **Hauptmenü → SumUp-Geräte**: OAuth connect/disconnect plus Solo pair/list/rename/unpair for org admins, tenant admins, and platform/superusers (active organisation context).
- Pairing requires a **label**; that label is what waiters and cash-register config choose (never raw `reader_id` in waiter UI).
- Payment types:
  - Keep slug `sumup`; rename display to **Sumup (manual)** (offline confirm, unchanged).
  - Add **Sumup connected** (`sumup_connected`): Cloud API reader checkout.
  - Remove / migrate off `stripe_terminal`.
- **Cash register:** default SumUp reader on the cash register (same binding idea as receipt printer).
- **Waiter:** choose SumUp device (by label) at waiter login; persist on session.
- Edge pay path: create/terminate/status reader checkout via cloud using the org’s OAuth tokens + platform Affiliate Key; confirm via webhook and/or polling; record payment with SumUp transaction id.
- Drop any replacement platform fee on card payments.

## Capabilities

### New Capabilities

- `sumup-cloud-connect`: Organisation SumUp OAuth linking, token storage/refresh, merchant identity, and the SumUp-Geräte admin surface (connect CTA + account status).
- `sumup-solo-readers`: Pair/list/update-label/unpair Solo readers under an organisation; labels as the human-facing identity for POS selection.
- `sumup-cloud-payments`: Event payment type `sumup_connected`, cash-register default reader, waiter login reader selection, Pi/edge Cloud API checkout lifecycle (create, terminate, confirm, persist).

### Modified Capabilities

- `stripe-connect`: Retire Connect/Terminal charge and fee requirements (capability removed from product).
- `stripe-terminal-device-support`: Retire Tap to Pay device gating and Android Terminal bridge requirements.
- `pi-admin-taptopay-status`: Retire Pi Admin Tap to Pay readiness UI requirements.
- `cloud-edge-security`: Replace Stripe webhook signature expectations with SumUp webhook verification where applicable.
- `register-order-settlement`: Settlement payment-type set gains `sumup_connected` and loses `stripe_terminal` (manual `sumup` retained with updated label).

## Impact

- **Cloud backend:** Remove `stripe_*` modules/routers/tests; add SumUp client (OAuth, readers, checkout, webhooks); org SumUp credential + reader tables; payment-type seed/fallback; OpenAPI regen.
- **Cloud frontend:** Remove Stripe Connect UI/help; add Hauptmenü SumUp-Geräte; payment-type i18n; cash-register reader binding UI.
- **Pi backend/frontend:** Remove Terminal proxy and Tap to Pay gating; add connected-checkout proxy; waiter login device picker; register default reader; payment labels/receipts.
- **Android:** Remove Stripe Terminal SDK, bridge, eligibility; APK becomes PWA shell without Tap to Pay.
- **Deps/ops:** Drop `stripe` Python package and `STRIPE_*` env vars; add `SUMUP_*` (OAuth client, Affiliate Key, webhook secret); update docs, website/privacy if they name Stripe as processor.
- **Data:** Migrate events that only enabled `stripe_terminal`; historical Stripe payment payloads remain readable for reports where possible.
