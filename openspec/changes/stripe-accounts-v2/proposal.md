## Why

New Stripe platforms (including the Vendiqo.ch Sandbox) reject Accounts v1 `Account.create(type="express")`, so organisation Connect onboarding fails with a generic "Stripe-Anfrage fehlgeschlagen" (HTTP 502). Stripe now requires Accounts v2 (`POST /v2/core/accounts`) for new Connect integrations. We need Connect create/refresh/status to work on modern sandboxes and live platforms without enabling the temporary Accounts v1 compatibility flag.

## What Changes

- Replace Accounts v1 Express account creation with Accounts v2 merchant-configured accounts suitable for **direct charges** (Terminal PaymentIntents on the connected account).
- Map readiness from v2 capability status (not deprecated v1 `charges_enabled` / `payouts_enabled` as the source of truth when reading from Stripe), while keeping the existing admin API response shape (`charges_enabled`, `payouts_enabled`, `details_submitted`) so the cloud UI does not break.
- Update account retrieve / Account Link creation to the APIs that work with v2 accounts.
- Keep Terminal PaymentIntent / ConnectionToken flows on the connected account (v1 PaymentIntents with `stripe_account` + `card_present`).
- Collect a **platform application fee of 0.2%** of each Terminal PaymentIntent amount (`application_fee_amount`), credited to the Vendiqo platform balance.
- Update Connect tests and `docs/stripe-connect-terminal.md` for the new create path and fee behaviour.
- **Not BREAKING** for the public cloud Connect REST contract or payment payload shape (`stripe_terminal` + `stripe_payment_intent_id`).

## Capabilities

### New Capabilities

- `stripe-connect`: Organisation-scoped Stripe Connect onboarding and readiness for Terminal direct charges (Accounts v2 create/link/refresh, denormalized org flags, webhook/status semantics, 0.2% platform application fee on Terminal charges).

### Modified Capabilities

- (none — no existing living spec covers Connect/Terminal today)

## Impact

- **Cloud backend**: `stripe_client.py`, `stripe_connect_status.py`, `routers/stripe_connect.py`, `routers/stripe_terminal.py` (fee on PI create), possibly webhook status mapping in `stripe_webhooks.py`; tests under `cloud/backend/tests/test_stripe_*.py`.
- **Cloud frontend**: no required UI/API shape change if status fields stay stable; help copy may mention Accounts v2 / fee only if docs change.
- **Docs**: `docs/stripe-connect-terminal.md` (fee rate and net settlement).
- **Stripe Dashboard**: platform must have Connect enabled; Accounts v2 available on the sandbox/platform (no reliance on `feat_accounts_v1_support`); application fees appear under Collected fees.
- **Existing connected accounts**: any leftover Accounts v1 Express accounts on the platform are out of scope for auto-migration; orgs without `stripe_account_id` get a new v2 account on next Connect click. Orgs already linked to a v1 account keep that id until manually cleared/re-onboarded.
- **Pi / Android / Terminal**: unchanged proxy and Tap to Pay UX; fee is applied server-side on PI create only.
