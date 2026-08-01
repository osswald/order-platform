## Context

Card acceptance today is Stripe Connect (Accounts v2) on `Organisation` plus Android Tap to Pay via Stripe Terminal, proxied through Pi edge APIs. The offline payment slug `sumup` is a manual label only. Product direction: physical SumUp Solo readers, SumUp Cloud API, one SumUp merchant per organisation, no platform fee, full Stripe removal.

## Goals / Non-Goals

**Goals:**
- Replace automated card payments with SumUp Cloud API checkouts on Solo readers.
- Organisation OAuth connect + reader management on **Hauptmenü → SumUp-Geräte** (org admin, tenant admin, platform/superuser).
- Required reader **labels** as the POS-facing identity.
- Cash-register default reader; waiter selects reader at login.
- Keep `sumup` as **Sumup (manual)**; add **Sumup connected** (`sumup_connected`); remove `stripe_terminal`.
- Remove Stripe code, deps, Android Terminal stack, fee, and related specs/docs.

**Non-Goals:**
- SumUp phone Tap to Pay / Reader SDKs.
- Platform application fee or SumUp revenue-share productization beyond Affiliate Key attribution.
- Pairing Solos as hire-company `Appliance` inventory reusable across merchants without re-pair.
- Migrating historical Stripe PaymentIntent rows into SumUp transaction ids.
- Online (card-not-present) SumUp checkouts.

## Decisions

1. **Auth = OAuth from day one**  
   Platform registers one SumUp OAuth app (`SUMUP_CLIENT_ID` / `SUMUP_CLIENT_SECRET`). Org admins authorize via authorization-code flow; cloud stores refresh/access tokens + `merchant_code` on the organisation. Affiliate Key (`SUMUP_AFFILIATE_KEY` + app id) is platform-level and attached to every reader checkout. Request SumUp activation of the `payments` scope early (manual vendor approval).

2. **SumUp-Geräte is the single admin surface (choice A)**  
   Nav item under HAUPTMENÜ, scoped to active organisation. Not connected → OAuth CTA. Connected → account status, disconnect, and reader CRUD. Do not bury OAuth under Organisation settings.

3. **Readers are merchant-scoped, not appliances**  
   Pairing is exclusive to one SumUp merchant. Cloud mirrors SumUp readers under `organisation_id` with `reader_id`, `label`, and status. Hire-company lending of physical Solos implies unpair/re-pair under the customer org’s merchant (new `reader_id` after re-pair).

4. **Label is required and is the picker identity**  
   Pairing API requires a non-empty label; stored locally and sent as SumUp reader `name`. Waiter login and cash-register config list labels only.

5. **Binding model**  
   - Cash register: optional `sumup_reader_id` (or local FK) on `EventCashRegister` — default for `sumup_connected` pays.  
   - Waiter: extend waiter session with selected reader id/label at login (localStorage); auto-select when exactly one org reader exists.

6. **Pay path**  
   Pi → cloud edge → SumUp `POST …/readers/{id}/checkout` with org token + affiliate metadata + amount/currency. Confirm via webhook (preferred) with polling fallback; support terminate. Persist payment `{ type: "sumup_connected", amount_cents, sumup_transaction_id, … }`. No application fee field.

7. **Payment-type migration**  
   Seed/fallback allowlist: `cash`, `twint`, `sumup`, `sumup_connected`. Deactivate `stripe_terminal`. Events that only had `stripe_terminal` get `sumup_connected` (or cash if org not ready—prefer replace slug and let runtime gating disable until OAuth+readers exist). Display rename for `sumup` → Sumup (manual).

8. **Stripe teardown**  
   Delete cloud Stripe modules/routers/UI/help, Pi Terminal routes, Android Stripe Terminal deps/bridge/eligibility, `STRIPE_*` env, `stripe` package. Historical order payloads may still contain `stripe_terminal` / `stripe_payment_intent_id` for read-only reporting labels.

9. **Edge security**  
   SumUp webhooks signature-verified; reader checkout edge routes require edge auth and event/org scope (same pattern as former Terminal routes).

10. **Nav / i18n**  
    German nav title: **SumUp-Geräte**. Payment labels: **Sumup (manual)** / **Sumup connected** (match product wording).

## Risks / Trade-offs

- **OAuth `payments` scope** may be blocked until SumUp manually activates the app — schedule vendor contact before go-live.
- **Solo exclusivity** means shared hire-company hardware needs operational re-pairing per org; cannot mirror printer appliances.
- **Concurrent checkouts** on one reader are rejected/locked (~60s); binding defaults reduce collisions but do not eliminate them.
- **Large teardown surface** (Android + cloud + Pi + docs) — prefer sequenced PR slices (types/UI labels → SumUp connect/readers → pay path → Stripe delete) if a single PR is too risky; specs still describe the end state.
- **Webhook delivery** to local/dev clouds needs tunnel or polling-heavy path; design MUST support polling fallback for reliability at the edge.
