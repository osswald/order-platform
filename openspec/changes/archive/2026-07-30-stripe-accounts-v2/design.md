## Context

Cloud Connect onboarding creates a Stripe connected account per `Organisation`, then Account Links for KYC. Terminal charges are **direct charges** on that account (`PaymentIntent.create(..., stripe_account=…)` with `card_present`). New Stripe platforms reject Accounts v1 `Account.create(type="express")`, which is what `stripe_client.create_connected_account` uses today — Connect clicks fail with HTTP 502 / `stripe_request_failed`.

Constraints:

- Keep secrets on cloud only; Pi/Android unchanged.
- Preserve admin API response fields used by `OrganisationStripeSection.vue`.
- Prefer Stripe’s current Connect guidance (Accounts v2 merchant config for SaaS/direct charges) over enabling the temporary Dashboard flag `feat_accounts_v1_support`.

## Goals / Non-Goals

**Goals:**

- Create connected accounts via Accounts v2 so new sandboxes/live platforms work.
- Derive org readiness from v2 merchant capability status; store denormalized booleans on `Organisation` for Terminal gates and admin chips.
- Keep Account Link onboarding UX (redirect to Stripe-hosted flow, return/refresh env URLs).
- Keep Terminal PI / connection-token paths on the connected account once the org is ready.
- Collect a **0.2% platform application fee** on each Terminal (`stripe_terminal`) PaymentIntent.

**Non-Goals:**

- Migrating existing Accounts v1 connected accounts automatically.
- Platform Billing / charging orgs as Stripe Customers (SaaS subscription independent of GMV).
- Destination charges or separate charges and transfers.
- Per-hire-company or per-org fee overrides (single platform-wide 0.2% for now).
- Changing Pi payment picker / Android Tap to Pay bridge.
- Bumping Stripe Python SDK solely for version fashion (only if v2 APIs require it).

## Decisions

### 1. Charge pattern: direct charges (unchanged)

- **Choice**: Continue creating Terminal PaymentIntents on the connected account.
- **Why**: Matches current product (org is merchant of record for card-present sales) and existing edge API.
- **Alternative**: Destination charges — rejected; would make the platform MoR and change Terminal Connect setup.

### 2. Accounts v2 merchant configuration (SaaS-style)

- **Choice** (locked by sandbox spike 2026-07-24): `POST /v2/core/accounts` via `StripeClient.v2.core.accounts.create` with:
  - `dashboard: "full"` — **required** for merchant + `fees_collector`/`losses_collector` = `stripe` on this platform (`express` returns `account_controller_unsupported_configuration`)
  - `identity.country` from organisation (e.g. `CH`), `identity.entity_type: "company"`, optional `business_details.registered_name`
  - `defaults.currency` (e.g. `chf`), `defaults.responsibilities.fees_collector` / `losses_collector` = `"stripe"`
  - `configuration.merchant.capabilities.card_payments.requested: true`
  - `metadata`: `organisation_id`, `hire_company_id`
  - retrieve/create `include`: `configuration.merchant`, `defaults`, `identity`, `requirements`, `future_requirements`
- **Account Links**: `StripeClient.v2.core.account_links.create` with `use_case.type=account_onboarding`, `configurations: ["merchant"]`, env return/refresh URLs — works against the v2 account id.
- **Alternative rejected**: `dashboard: "express"` with the same merchant/responsibility combo (unsupported on Vendiqo.ch Sandbox).
- **Alternative deferred**: marketplace `fees_collector`/`losses_collector` = `application` (not needed for direct-charge SaaS).

### 3. Stable admin API shape; map from v2 capabilities

- **Choice**: Continue exposing `charges_enabled`, `payouts_enabled`, `details_submitted` on Connect status endpoints.
- **Mapping** (locked from spike retrieve shape):
  - `charges_enabled` ← `configuration.merchant.capabilities.card_payments.status == "active"`
  - `payouts_enabled` ← `configuration.merchant.capabilities.stripe_balance.payouts.status == "active"`
  - `details_submitted` ← no `requirements.entries` with `awaiting_action_from == "user"` and `minimum_deadline.status` in (`currently_due`, `past_due`)  
    (pre-onboarding fixture has `card_payments.status == "restricted"` with `requirements_past_due`)
- Fixtures: `openspec/changes/stripe-accounts-v2/spike/v2_account_not_ready.slim.json` (+ synthetic ready slim).
- **Why**: Avoid frontend/OpenAPI churn; Terminal gate already uses `organisation.stripe_charges_enabled`.
- **Alternative**: Expose raw capability enums in the API — deferred.

### 4. Account Links

- **Choice** (spike-confirmed): Use **v2** Account Links (`POST /v2/core/account_links`) against the v2 account id. Return/refresh URLs remain env-only (`STRIPE_CONNECT_RETURN_URL` / `STRIPE_CONNECT_REFRESH_URL`), never client-supplied.

### 5. Webhooks

- **Choice**: Keep listening for v1 `account.updated` for MVP — Stripe documents that merchant-config updates on v2 accounts still emit v1 `account.updated` (Connected accounts scope). Map payload → org flags via the same helper used by refresh (retrieve-with-include if the snapshot is incomplete).
- Add thin `v2.core.account.*` destinations only if sandbox onboarding proves v1 events insufficient.
- `payment_intent.succeeded` stays audit-only.

### 6. Stripe client surface

- **Choice** (spike-confirmed): Use `stripe.StripeClient` + `v2.core.accounts` / `v2.core.account_links` on pinned **stripe 15.3.1** — **no package bump required** for Connect create/retrieve/link. Keep classic PaymentIntent/Terminal APIs for charges. Preserve router-facing function names where practical so tests keep patching the same symbols.

### 7. Existing org rows

- **Choice**: If `stripe_account_id` is already set (v1 leftover), refresh/link against that id; do not auto-delete. New orgs (null id) create v2 accounts. Ops can clear `stripe_account_id` to force re-create if a stale v1 account cannot be linked.

### 8. Platform fee: 0.2% per Terminal transaction

- **Choice**: On `create_terminal_payment_intent`, set `application_fee_amount` to **0.2%** of `amount_cents` (20 basis points), using direct-charge net settlement (fee deducted before funds settle to the org).
- **Formula**: `fee_cents = (amount_cents * 20 + 5000) // 10000` (integer half-up to nearest cent). If `fee_cents < 1`, omit `application_fee_amount` (Stripe requires a positive fee). If `fee_cents >= amount_cents`, clamp so fee is strictly less than amount (should not occur at 0.2%).
- **Scope**: Only Terminal / `stripe_terminal` PaymentIntents created by the cloud edge path. Cash / TWINT / SumUp unchanged.
- **Config**: Constant or env default (e.g. `STRIPE_PLATFORM_FEE_BPS=20`) with default 20; no per-tenant overrides in this change.
- **Refunds**: When refunding a Terminal charge later, refund the application fee proportionally (`refund_application_fee=true` on charge refunds, or equivalent). If no refund API exists yet for Terminal, document as follow-up so orgs are not left short on full refunds.
- **Why 0.2%**: Light take-rate on card GMV; software/hire remains primary monetization; org still pays Stripe processing fees separately (`fees_collector = stripe`).
- **Alternative**: Software-only (0%) — rejected for this change after product decision. Higher take-rate (0.5%+) — deferred.

```
Customer pays amount
        │
        ▼
PI on org account (direct charge)
  application_fee_amount = 0.2%
        ├─► Platform balance  + fee
        └─► Org balance       amount − fee − Stripe fees
```

## Risks / Trade-offs

- [Risk] Sandbox requires Accounts v2 early-access / platform Connect onboarding incomplete → Mitigation: document Dashboard prerequisites in `docs/stripe-connect-terminal.md`; surface Stripe error message in logs (and optionally richer API errors later).
- [Risk] Capability field paths differ from assumed mapping → Mitigation: **closed by spike**; unit-test mapper with slim fixtures.
- [Risk] Mixed v1/v2 accounts on one platform → Mitigation: document; Terminal still works per-account once capabilities active.
- [Risk] Account Link API mismatch (v1 vs v2) → Mitigation: **closed by spike** — use v2 account_links.
- [Risk] Full refunds without refunding application fee leave the org short → Mitigation: define refund behaviour in Terminal refund path or document explicit follow-up.
- [Risk] `dashboard: full` means orgs get the full Stripe Dashboard (not Express) → Mitigation: accept for SaaS/direct charges; document in admin help that orgs manage payouts in Stripe.
- [Trade-off] Denormalized boolean columns lag Stripe until refresh/webhook → Acceptable; already the model today.
- [Trade-off] Tiny amounts may round to 0 fee → Acceptable at 0.2%; no minimum floor in this change.

## Migration Plan

1. Ship backend change behind normal deploy; no DB migration required if columns stay the same.
2. Ensure sandbox/live platform has Connect + Accounts v2 enabled.
3. For orgs that never got an account id: Connect works on next click.
4. For orgs stuck with a non-onboardable v1 id: clear `stripe_account_id` (admin/SQL) and re-run Connect.
5. Rollback: revert deploy; optionally re-enable Accounts v1 Dashboard flag if needed for emergency.

## Open Questions

~~1. Exact `dashboard` / responsibility fields…~~ **Closed** — `dashboard: full` + merchant `card_payments` + `fees_collector`/`losses_collector` = `stripe` (see Decision 2). Spike account `acct_1TwrwwBlfNu9f1Sp`.

~~2. Whether v1 `account.updated` alone is enough…~~ **Closed for implementation plan** — keep v1 `account.updated` for MVP per Stripe docs; verify on first real onboarding; add v2 destinations only if needed.

~~3. Whether Stripe Python `15.x` exposes v2…~~ **Closed** — `stripe==15.3.1` `StripeClient.v2.core.accounts` / `account_links` works; no bump required.

**Spike KYC note (2026-07-24/25):** With `requirements_collector: stripe` (and after an Account Link exists), the platform **cannot** accept ToS or write person DOB / bank via API. Sandbox KYC **must** use the hosted Account Link flow.

**Verified after hosted KYC** on `acct_1TwrwwBlfNu9f1Sp`:
- `configuration.merchant.capabilities.card_payments.status` → `active`
- `configuration.merchant.capabilities.stripe_balance.payouts.status` → `active`
- user-facing `requirements.entries` → empty
- v1 `account.updated` webhooks delivered via `stripe listen` and stored in `stripe_webhook_events` (Q2 closed in practice)
