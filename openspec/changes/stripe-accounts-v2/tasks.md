## 1. Spike and fixtures

- [x] 1.1 Against Vendiqo.ch Sandbox, confirm Accounts v2 create payload (merchant config, dashboard, responsibilities) that accepts CH company/org metadata and returns an account id
- [x] 1.2 Confirm Account Link create path for that account id (v1 vs v2 link API) and capture a sample retrieve JSON for capability mapping
- [x] 1.3 Add fixture JSON under `openspec/changes/stripe-accounts-v2/spike/` (slim not-ready + synthetic ready) for capability mapping

## 2. Tests first

- [x] 2.1 Extend/replace `test_stripe_connect_api.py` so account-link mocks assert Accounts v2 create (no `type=express` v1 create) and env-only return/refresh URLs
- [x] 2.2 Add unit tests for status mapping: inactive card_payments → `charges_enabled` false; active → true (and payouts/details mapping from fixtures)
- [x] 2.3 Keep Terminal readiness tests asserting edge PI creation still requires denormalized `stripe_charges_enabled` / connected account id

## 3. Client and status mapping

- [x] 3.1 Implement Accounts v2 create + retrieve in `stripe_client.py` (bump `stripe` package only if SDK lacks v2 helpers)
- [x] 3.2 Update `stripe_connect_status.py` to map v2 capability/requirements fields into organisation boolean columns; keep webhook path using the same helpers
- [x] 3.3 Wire Account Link creation for v2 accounts; leave router auth/tenancy and response models unchanged unless types require minor adjustments

## 4. Platform fee (0.2%)

- [x] 4.1 Add unit tests for fee helper: 1000 → 2 cents; tiny amounts → omit fee; fee never ≥ amount
- [x] 4.2 Implement 20 bps `application_fee_amount` on `create_terminal_payment_intent` (constant or `STRIPE_PLATFORM_FEE_BPS` default 20)
- [x] 4.3 Update Terminal API tests so mocked PI create asserts the fee argument
- [x] 4.4 Document fee rate, net settlement, and refund follow-up in `docs/stripe-connect-terminal.md`

## 5. Docs and verification

- [x] 5.1 Update `docs/stripe-connect-terminal.md` (Accounts v2, Dashboard prerequisites, no reliance on Accounts v1 feature flag)
- [x] 5.2 Run cloud backend Stripe Connect/Terminal related tests and `./scripts/lint.sh` for touched areas
- [x] 5.3 Manual check: Connect from `/organisations/{id}?section=stripe` creates an account and returns a Stripe onboarding URL (sandbox)
