# SumUp Cloud API integration

> **Note:** Stripe Connect and Stripe Terminal Tap to Pay were removed from Vendiqo.
> Card payments now run via the **SumUp Cloud API** (OAuth connect, Solo readers, edge checkouts).

Organisations connect SumUp in the cloud admin under **SumUp devices**. In-person card payments use SumUp Solo readers assigned to cash registers; the Pi/Android clients call cloud edge endpoints with existing appliance credentials — no SumUp secrets on edge devices.

## Ownership model

- SumUp OAuth tokens belong to an `Organisation`.
- `HireCompany` remains the tenant/security boundary for admins and appliances.
- Raspberry Pi devices proxy checkout and reader status to cloud edge routes using `X-Edge-Client-Id` / `X-Edge-Secret`.

## Configuration (cloud)

Set in `cloud/.env`:

| Variable | Purpose |
|----------|---------|
| `SUMUP_CLIENT_ID` / `SUMUP_CLIENT_SECRET` | OAuth app credentials |
| `SUMUP_REDIRECT_URI` | OAuth callback URL (cloud frontend route) |
| `SUMUP_WEBHOOK_SECRET` | Webhook signature verification |
| `SUMUP_AFFILIATE_KEY` / `SUMUP_AFFILIATE_APP_ID` | Optional affiliate metadata |

After OAuth, admins manage readers on **SumUp devices** and assign a reader per cash register in event configuration.

## Event activation

In event configuration under master data enable payment type **SumUp connected** and assign a SumUp reader to each cash register that accepts cards.

## Edge flow (Pi)

1. Waiter selects **SumUp connected** in the payment picker (requires cloud reachability).
2. Pi calls `/edge/v1/sumup/checkout` on cloud via local proxy.
3. Cloud drives the assigned Solo reader; Pi stores `sumup_transaction_id` on the payment row.

## Legacy Stripe documentation

The previous Stripe Connect / Terminal design is archived in git history (`docs/stripe-connect-terminal.md` prior to removal). Do not use Stripe env vars or routes — they are no longer mounted.
