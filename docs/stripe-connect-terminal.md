# Stripe Connect and Terminal integration

This repository now has the first integration seam for organisations that want
their own Stripe account connected in the cloud and in-person card payments
collected from Android waiter devices.

## Ownership model

- A Stripe connected account belongs to an `Organisation`.
- `HireCompany` (`Verleiher`) remains the tenant/security boundary for admins
  and appliances, but payouts and Terminal charges are scoped to the event's
  organisation.
- Raspberry Pi devices and Android devices never receive the platform Stripe
  secret key. They call Pi-local endpoints, which proxy to cloud edge endpoints
  using existing `X-Edge-Client-Id` / `X-Edge-Secret` credentials.

## Cloud endpoints

Cloud admin onboarding:

- `GET /stripe/connect/organisations/{organisation_id}/status`
- `POST /stripe/connect/organisations/{organisation_id}/account-link`
- `POST /stripe/connect/organisations/{organisation_id}/refresh`

The onboarding request returns a Stripe Account Link for the selected
organisation. The cloud stores the connected account id and readiness flags on
`organisations`.

Edge-authenticated Terminal endpoints:

- `POST /edge/v1/terminal/connection-token`
- `POST /edge/v1/terminal/payment-intents`
- `GET /edge/v1/terminal/payment-intents/{payment_intent_id}?event_id=...`

The cloud creates Terminal PaymentIntents on the connected account using
`payment_method_types=["card_present"]`, which is the Terminal-specific
exception to the general rule of not hard-coding payment method types.

## Pi and Android flow

1. Cloud admin connects the event organisation to Stripe and enables
   `stripe_terminal` as an event payment type.
2. Pi sync pulls the event bundle and exposes `stripe_terminal` locally.
3. The waiter selects "Karte" in the Android WebView.
4. The PWA calls `POST /v1/terminal/payment-intents` on the Pi.
5. The Pi proxies the request to cloud and receives a PaymentIntent client
   secret.
6. The PWA calls the native `window.AndroidTerminal.collectPayment(...)` bridge.
7. Kotlin uses Stripe Terminal SDK to discover/connect the reader, collect the
   payment method, and confirm the PaymentIntent.
8. The PWA records the completed payment as:

```json
{
  "type": "stripe_terminal",
  "amount_cents": 1200,
  "stripe_payment_intent_id": "pi_..."
}
```

The order/payment payload then syncs to cloud through the existing outbox.

## Android bridge contract

`pi/frontend/src/utils/androidTerminal.js` expects a native object:

```kotlin
webView.addJavascriptInterface(stripeTerminalBridge, "AndroidTerminal")
```

Minimum bridge method:

```kotlin
@JavascriptInterface
fun collectPayment(connectionTokenSecret: String, paymentIntentClientSecret: String): String
```

Return JSON:

```json
{ "ok": true, "payment_intent_id": "pi_..." }
```

or:

```json
{ "ok": false, "error": "Reader disconnected" }
```

The native implementation should add Stripe Terminal SDK, Android location/NFC
permissions as required by the selected reader mode, and manage reader
discovery/reconnect lifecycle outside the WebView.

## Required configuration

Cloud:

```env
STRIPE_SECRET_KEY=rk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CONNECT_RETURN_URL=https://admin.vendiqo.ch/settings/stripe/return
STRIPE_CONNECT_REFRESH_URL=https://admin.vendiqo.ch/settings/stripe/refresh
```

Use a restricted Stripe key with the minimum permissions needed for Connect,
Account Links, Terminal Connection Tokens, and PaymentIntents.

## Remaining production work

- Add the cloud admin UI panel for Connect onboarding status and account-link
  launch.
- Implement `StripeTerminalBridge.kt` with the Stripe Terminal Android SDK.
- Gate the "Karte" picker action on cloud connectivity because Terminal cannot
  complete offline.
- Add Stripe webhooks for `account.updated` and `payment_intent.succeeded` to
  reconcile onboarding status and payment completion.
