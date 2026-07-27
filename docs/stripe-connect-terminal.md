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

## Account model (Accounts v2)

Connected accounts are created with the **Accounts v2** API
(`POST /v2/core/accounts`, via `StripeClient.v2.core.accounts`). Accounts v1
`Account.create(type="express")` is not used — new Stripe platforms reject it,
and we do not rely on the temporary `feat_accounts_v1_support` Dashboard flag.

Create payload (see `cloud/backend/app/stripe_client.py`):

| Field | Value |
|-------|-------|
| `dashboard` | `full` — required alongside `fees_collector`/`losses_collector` = `stripe`; `express` is rejected for this combination |
| `identity.country` / `entity_type` | organisation country (default `CH`), `company` |
| `defaults.currency` | organisation currency, lowercased |
| `defaults.responsibilities` | `fees_collector` and `losses_collector` = `stripe` |
| `configuration.merchant.capabilities.card_payments.requested` | `true` |
| `metadata` | `organisation_id`, `hire_company_id` |

Onboarding uses **v2 Account Links** (`use_case.type = account_onboarding`,
`configurations: ["merchant"]`). Return and refresh URLs always come from
environment configuration; values in the request body are ignored.

Because `requirements_collector` is `stripe`, KYC must be completed in the
Stripe-hosted Account Link flow — the platform cannot accept terms of service
or submit person/bank details through the API.

Organisation readiness flags are mapped from the retrieved account:

| Organisation column | Accounts v2 source |
|---------------------|--------------------|
| `stripe_charges_enabled` | `configuration.merchant.capabilities.card_payments.status == "active"` |
| `stripe_payouts_enabled` | `configuration.merchant.capabilities.stripe_balance.payouts.status == "active"` |
| `stripe_details_submitted` | no `requirements.entries` awaiting the user with a `currently_due`/`past_due` deadline |

`account.updated` webhooks still deliver an Accounts v1 shaped snapshot; the same
mapper falls back to the top-level `charges_enabled` / `payouts_enabled` /
`details_submitted` fields for those payloads.

Existing organisations that already hold an Accounts v1 `stripe_account_id` keep
it — onboarding links are minted against that id. To force re-creation on v2,
clear `stripe_account_id` for the organisation.

**Dashboard prerequisites:** Connect must be enabled on the platform account, and
`dashboard: full` means connected organisations manage payouts in the full Stripe
Dashboard rather than an Express dashboard.

## Platform fee

Terminal charges are **direct charges** on the connected account, and the platform
takes an `application_fee_amount` of **0.2%** (20 basis points) of the
PaymentIntent amount, rounded half-up to the nearest minor unit. The fee is
deducted before funds settle to the organisation; the organisation still pays
Stripe processing fees separately (`fees_collector = stripe`).

- Configurable via `STRIPE_PLATFORM_FEE_BPS` (default `20`, `0` disables).
- Fees below one minor unit are omitted, since Stripe requires a positive amount.
- Only `stripe_terminal` PaymentIntents are charged; cash, TWINT, and SumUp are not.

**Follow-up:** there is no Terminal refund path yet. When one is added, it must
refund the application fee proportionally (`refund_application_fee`), otherwise a
full refund leaves the organisation short by the fee.

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
3. **Device supports Tap to Pay** — native `AndroidTerminal.supportsTapToPay()` (Stripe
   Terminal `supportsReadersOfType` for Tap to Pay). Best-effort: some Stripe soft
   criteria (rooted device, Developer options, stale security patch) may still fail
   only at discover/connect. Older APKs without `supportsTapToPay` keep prior
   enablement (fail open for device support).

Hints under a disabled button (priority order):

- «Nur in der Android-App verfügbar.»
- «Cloud-Verbindung erforderlich.»
- «Standortberechtigung für Kartenzahlung erforderlich.» (cannot evaluate support)
- «Gerät unterstützt keine Kartenzahlung (Tap to Pay).»

## Pi Admin: versions and Tap to Pay readiness

On the Pi Admin hub (Android only), below the existing **App** (PWA) and **Pi**
(backend) version lines:

- **Android** — native APK `versionName` from `AndroidApp.getAppInfo()`
- **Tap to Pay** — device readiness from `AndroidTerminal.supportsTapToPay()` run
  when Admin loads (re-checked each open). Labels: bereit / bereit (simuliert) /
  Standort fehlt / nicht unterstützt / Fehler. This is **device-only** readiness
  (hardware + location + SDK init); it does **not** verify org Stripe Connect
  onboarding or that a real card charge will succeed. When any eligibility check
  fails, Admin also lists each check (location, Android 13+, NFC, hardware
  keystore, GMS, security patch, developer options, internet, Stripe SDK) with
  pass/fail. The checklist is hidden when the device is ready.

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

`pi/frontend/src/utils/androidTerminal.ts` expects:

```kotlin
webView.addJavascriptInterface(stripeTerminalBridge, "AndroidTerminal")
```

Methods:

```kotlin
@JavascriptInterface
fun supportsTapToPay(): String

@JavascriptInterface
fun collectPayment(connectionTokenSecret: String, paymentIntentClientSecret: String): String
```

`supportsTapToPay` return JSON:

```json
{ "ok": true, "supported": true }
```

```json
{ "ok": true, "supported": false, "error": "…" }
```

```json
{ "ok": false, "error": "Standortberechtigung für Kartenzahlung erforderlich." }
```

`collectPayment` return JSON:

```json
{ "ok": true, "payment_intent_id": "pi_..." }
```

or:

```json
{ "ok": false, "error": "Reader disconnected" }
```

Implementation: `android/app/.../StripeTerminalBridge.kt` with
`stripeterminal-taptopay` + `stripeterminal-core` (see `app/build.gradle.kts`).
`minSdk` is 33 for Tap to Pay. Location permission is required for both support
check and collect. Debug builds use simulated Tap to Pay discovery for both.

## Required configuration

Cloud:

```env
STRIPE_SECRET_KEY=rk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CONNECT_RETURN_URL=https://admin.vendiqo.ch/settings/stripe/return
STRIPE_CONNECT_REFRESH_URL=https://admin.vendiqo.ch/settings/stripe/refresh
STRIPE_PLATFORM_FEE_BPS=20
```

Use a restricted Stripe key with Connect, Account Links, Terminal Connection Tokens,
and PaymentIntents.

Pi: cloud pairing (`CLOUD_BASE_URL`, edge credentials) — no `STRIPE_*` on Pi.

Stripe Dashboard: enable **Tap to Pay on Android** for the platform and connected accounts.

## Manual test PDFs

- **Full platform:** [`vendiqo-full-test-scenarios.pdf`](vendiqo-full-test-scenarios.pdf) — all features (cloud, Pi, Android)
- **Stripe Connect / Terminal only:** [`stripe-terminal-test-scenarios.pdf`](stripe-terminal-test-scenarios.pdf)

Regenerate:

```bash
python3 docs/generate_full_app_test_pdf.py
python3 docs/generate_stripe_terminal_test_pdf.py
```

## Manual test checklist

| Scenario | Expected |
|----------|----------|
| Browser PWA, event has Karte | Karte button visible, **disabled** |
| Android offline / cloud down | Karte **disabled**, cloud hint |
| Android online, unsupported device (no NFC / fails SDK check) | Karte **disabled**, device Tap to Pay hint |
| Android online, location permission denied | Karte **disabled**, location hint |
| Android online, org not onboarded | Karte enabled; payment fails at PI creation (409) |
| Connect onboarding in cloud | Status chips update; `charges_enabled` true |
| Event + Karte enabled, Android online, supported device | Tap to Pay flow completes; payment has `stripe_payment_intent_id` |
| Webhook `account.updated` | Organisation flags refresh without manual refresh |

## Troubleshooting

- **503 Stripe not configured** — set `STRIPE_SECRET_KEY` on cloud backend.
- **Karte disabled on Android** — check location permission and `GET /v1/cloud/reachable`.
- **Terminal SDK errors** — device must support Tap to Pay (GMS, NFC); use Stripe test mode / simulated reader in debug builds.
