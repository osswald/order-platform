## 1. Payment types and labels

- [x] 1.1 Add failing tests for payment-type seed/fallback: `sumup_connected` active, `sumup` label Sumup (manual), `stripe_terminal` inactive
- [x] 1.2 Update cloud payment-type seed, fallback allowlist, sales/receipt/i18n labels (manual + connected); migrate events that only had `stripe_terminal`
- [x] 1.3 Update Pi payment-type allowlist, picker labels, and receipt labels to match

## 2. SumUp OAuth connect (cloud)

- [x] 2.1 Add failing API tests for OAuth start/callback/disconnect and org-admin access control
- [x] 2.2 Add org SumUp credential fields/tables, `SUMUP_*` env, SumUp OAuth client (token exchange/refresh)
- [x] 2.3 Implement connect/callback/disconnect/status routes; regenerate OpenAPI types
- [x] 2.4 Build Hauptmenü **SumUp-Geräte** page with connect CTA and connected account status (org/tenant/superuser)

## 3. Solo reader management

- [x] 3.1 Add failing API/UI tests for pair (code + required label), list, rename label, unpair
- [x] 3.2 Persist org-scoped readers (`reader_id`, label, status); call SumUp Readers API with org token
- [x] 3.3 Complete SumUp-Geräte reader UI (pair form, label list, rename, unpair); sync reader list into edge event bundle as needed

## 4. POS binding (register + waiter)

- [x] 4.1 Add failing tests for cash-register default reader binding and waiter login device selection (incl. single-reader auto-select)
- [x] 4.2 Cloud: cash-register config field for default SumUp reader (by label); include in event bundle
- [x] 4.3 Pi: waiter login picker for labelled readers; persist on waiter session; register uses default reader for `sumup_connected`

## 5. Cloud API checkout pay path

- [x] 5.1 Add failing edge/Pi tests for create checkout, terminate, confirm (webhook + poll), payment payload with `sumup_transaction_id`, no platform fee
- [x] 5.2 Cloud edge SumUp checkout/terminate/status + webhook verification; Affiliate Key on checkout; edge auth/event scope
- [x] 5.3 Pi proxy + `resolvePayment` / settlement paths for `sumup_connected`; remove Stripe Terminal PI flow from payment resolution

## 6. Stripe teardown

- [x] 6.1 Remove cloud Stripe modules, routers, org stripe columns usage, webhooks, Connect UI/help, tests, and `stripe` dependency / `STRIPE_*` env
- [x] 6.2 Remove Pi Terminal routes, Tap to Pay gating, Admin Tap to Pay status UI, and related tests
- [x] 6.3 Remove Android Stripe Terminal SDK, bridge, eligibility, and init; keep PWA shell usable without Tap to Pay
- [x] 6.4 Update docs (`stripe-connect-terminal`, test PDFs, AGENTS/README/privacy/website) to SumUp Cloud API; drop Stripe fee docs

## 7. Verification

- [x] 7.1 Run cloud + Pi backend tests and regenerate OpenAPI types if schemas changed
- [x] 7.2 Run cloud + Pi frontend tests / typecheck as applicable
- [x] 7.3 Run `./scripts/lint.sh` on touched areas
