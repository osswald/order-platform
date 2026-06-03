# Stripe Connect and Terminal integration

Organisations connect their own Stripe account in the cloud admin UI. In-person
contactless payments run on Android waiter devices via **Tap to Pay** (Stripe
Terminal SDK). Raspberry Pi and Android never receive the platform Stripe secret;
they use Pi-local APIs that proxy to cloud edge endpoints with existing appliance
credentials.

## Ownership model

- A Stripe connected account belongs to an `Organisation`.
- `HireCompany` (`Verleiher`) remains the tenant/security boundary for admins
  and appliances, but payouts and Terminal charges are scoped to the event's
  organisation.
- Raspberry Pi devices and Android devices never receive the platform Stripe
  secret key. They call Pi-local endpoints, which proxy to cloud edge endpoints
  using existing `X-Edge-Client-Id` / `X-Edge-Secret` credentials.

## Cloud endpoints

Cloud admin onboarding (`tenant admin`):

- `GET /stripe/connect/organisations/{organisation_id}/status`
- `POST /stripe/connect/organisations/{organisation_id}/account-link`
- `POST /stripe/connect/organisations/{organisation_id}/refresh`

UI: **Organisationen** → organisation detail → section **Kartenzahlung (Stripe)**.

Return URLs (configure in cloud `.env`):

- `STRIPE_CONNECT_RETURN_URL` → `https://<admin-host>/settings/stripe/return`
- `STRIPE_CONNECT_REFRESH_URL` → `https://<admin-host>/settings/stripe/refresh`

Webhooks:

- `POST /stripe/webhooks` — events: `account.updated`, `payment_intent.succeeded`
- Set `STRIPE_WEBHOOK_SECRET` from the Stripe Dashboard endpoint signing secret.

Edge-authenticated Terminal endpoints:

- `POST /edge/v1/terminal/connection-token`
- `POST /edge/v1/terminal/payment-intents`
- `GET /edge/v1/terminal/payment-intents/{payment_intent_id}?event_id=...`

The cloud creates Terminal PaymentIntents on the connected account using
`payment_method_types=["card_present"]`, which is the Terminal-specific
exception to the general rule of not hard-coding payment method types.

## Pi endpoints

- `GET /v1/cloud/reachable` — short probe to cloud `/health` (gates Terminal in UI)
- `POST /v1/terminal/connection-token` — proxy to cloud
- `POST /v1/terminal/payment-intents` — proxy to cloud
- `GET /v1/terminal/payment-intents/{id}?event_id=...` — proxy to cloud

## Payment type availability (Pi PWA)

Event flag: **Karte (Stripe Terminal)** (`stripe_terminal`) in cloud event config.

The picker **always shows** Karte when enabled on the event, but the button is
**disabled** unless:

1. **Android app** — WebView with `AndroidTerminal` bridge / `PiFrontendAndroid` user agent
2. **Cloud reachable** — `GET /v1/cloud/reachable` succeeds (internet; Terminal APIs need cloud)

Hints under a disabled button: «Nur in der Android-App verfügbar.» / «Cloud-Verbindung erforderlich.»

## Android Tap to Pay flow

1. Cloud admin connects the event organisation to Stripe and enables
   `stripe_terminal` as an event payment type.
2. Pi sync pulls the event bundle and exposes `stripe_terminal` locally.
3. Waiter selects **Karte** (enabled only on Android with cloud).
4. PWA calls `POST /v1/terminal/payment-intents` on the Pi.
5. Pi proxies to cloud and returns a PaymentIntent client secret.
6. PWA calls `POST /v1/terminal/connection-token`, then native
   `window.AndroidTerminal.collectPayment(connectionToken, clientSecret)`.
7. Kotlin (Stripe Terminal SDK, Tap to Pay) discovers/connects the on-device reader,
   collects the card, and confirms the PaymentIntent.
8. PWA records:

```json
{
  "type": "stripe_terminal",
  "amount_cents": 1200,
  "stripe_payment_intent_id": "pi_..."
}
```

The order/payment payload syncs to cloud through the existing outbox.

### Android bridge contract

`pi/frontend/src/utils/androidTerminal.js` expects:

```kotlin
webView.addJavascriptInterface(stripeTerminalBridge, "AndroidTerminal")
```

Minimum method:

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

Implementation: `android/app/.../StripeTerminalBridge.kt` with
`stripeterminal-taptopay` + `stripeterminal-core` (see `app/build.gradle.kts`).
`minSdk` is 33 for Tap to Pay. Location permission is required.

## Required configuration

Cloud:

```env
STRIPE_SECRET_KEY=rk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CONNECT_RETURN_URL=https://admin.vendiqo.ch/settings/stripe/return
STRIPE_CONNECT_REFRESH_URL=https://admin.vendiqo.ch/settings/stripe/refresh
```

Use a restricted Stripe key with Connect, Account Links, Terminal Connection Tokens,
and PaymentIntents.

Pi: cloud pairing (`CLOUD_BASE_URL`, edge credentials) — no `STRIPE_*` on Pi.

Stripe Dashboard: enable **Tap to Pay on Android** for the platform and connected accounts.

## Manual test checklist

| Scenario | Expected |
|----------|----------|
| Browser PWA, event has Karte | Karte button visible, **disabled** |
| Android offline / cloud down | Karte **disabled**, cloud hint |
| Android online, org not onboarded | Karte enabled; payment fails at PI creation (409) |
| Connect onboarding in cloud | Status chips update; `charges_enabled` true |
| Event + Karte enabled, Android online | Tap to Pay flow completes; payment has `stripe_payment_intent_id` |
| Webhook `account.updated` | Organisation flags refresh without manual refresh |

## Troubleshooting

- **503 Stripe not configured** — set `STRIPE_SECRET_KEY` on cloud backend.
- **Karte disabled on Android** — check location permission and `GET /v1/cloud/reachable`.
- **Terminal SDK errors** — device must support Tap to Pay (GMS, NFC); use Stripe test mode / simulated reader in debug builds.
