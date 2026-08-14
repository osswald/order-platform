# SumUp Cloud API integration

> **Note:** Stripe Connect and Stripe Terminal Tap to Pay were removed from Vendiqo.
> Card payments now run via the **SumUp Cloud API** (merchant API-key connect, Solo readers, edge checkouts).
> Organisation OAuth authorize/callback remains in the backend for a future SumUp `payments` scope approval, but is **not** the admin connect path.

Organisations connect SumUp in the cloud admin under **SumUp devices** by pasting a merchant **API key** from the SumUp dashboard (Settings → For Developers → Toolkit → API Keys). In-person card payments use SumUp Solo readers assigned to cash registers; the Pi/Android clients call cloud edge endpoints with existing appliance credentials — no SumUp secrets on edge devices.

## Ownership model

- SumUp credentials (API key, or dormant OAuth tokens) belong to an `Organisation`.
- `HireCompany` remains the tenant/security boundary for admins and appliances.
- Raspberry Pi devices proxy checkout and reader status to cloud edge routes using `X-Edge-Client-Id` / `X-Edge-Secret`.

## Configuration (cloud)

Set in `cloud/.env`:

| Variable | Purpose |
|----------|---------|
| `SUMUP_AFFILIATE_KEY` / `SUMUP_AFFILIATE_APP_ID` | Required for Solo checkout attribution (platform-level) |
| `SUMUP_WEBHOOK_SECRET` | Webhook signature verification |
| `SUMUP_CLIENT_ID` / `SUMUP_CLIENT_SECRET` / `SUMUP_REDIRECT_URI` | Optional while OAuth is dormant (only needed to revive OAuth connect) |

After connecting with an API key, **SumUp devices** shows merchant name, merchant code, country, and whether SumUp reports the account as **Sandbox** or **Live** (`GET /v1/merchants/{merchant_code}` `sandbox` flag). One API key often spans several merchants (live + sandboxes); connect lists SumUp memberships and asks you to pick one when there is more than one — do not rely on SumUp `/me`, which returns only the default live merchant. Use **Update API key** to rotate the key for the same merchant without re-pairing readers; **Disconnect** clears credentials and local reader rows.

Solo reader checkouts use the Readers Cloud API (`POST …/readers/{id}/checkout` → nested `data.checkout_id` / `client_transaction_id`, then poll `GET …/readers/{id}/checkout/{checkout_id}`). Do not use online `GET /v0.1/checkouts/{id}` for Solo status.

## Event activation

In event configuration under master data enable payment type **SumUp connected** and assign a SumUp reader to each cash register that accepts cards.

## Edge flow (Pi)

1. Waiter selects **SumUp connected** in the payment picker (requires cloud reachability).
2. Pi calls `/edge/v1/sumup/checkout` on cloud via local proxy.
3. Cloud drives the assigned Solo reader; Pi stores `sumup_transaction_id` on the payment row.

## Legacy Stripe documentation

The previous Stripe Connect / Terminal design is archived in git history (`docs/stripe-connect-terminal.md` prior to removal). Do not use Stripe env vars or routes — they are no longer mounted.
