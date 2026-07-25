## 1. Setup and inventory

- [x] 1.1 Create feature branch from `main` for this change
- [x] 1.2 Inventory auth, tenancy, edge, Stripe, hosted-Pi manager, and config entry points against the design threat model
- [x] 1.3 Create `openspec/changes/cloud-security-audit/findings.md` with severity columns (Critical/High/Medium/Low/Info), surface, evidence path, and status

## 2. Threat model refinement (B)

- [x] 2.1 Refine actors, assets, and trust boundaries in `design.md` with any gaps found during inventory
- [x] 2.2 Confirm abuse-case priority order from design (tenancy → edge → session/CSRF → Terminal → hosted-Pi → deploy/config) or document an agreed reordering
- [x] 2.3 Record resolved decisions D5/D7/D8/D4 in `findings.md` assumptions (HttpOnly access in scope; single-container rate limits; Terminal vs hosted-Pi split; Christoph accepts Medium/Low)

## 3. Surface review — admin auth and session (C)

- [x] 3.1 Review login, refresh, logout, `token_version`, cookie flags, and Bearer/`typ` separation against baseline and `cloud-session-jwt`
- [x] 3.2 Review current frontend `localStorage` access-token usage and map all call sites that must switch to credentialed cookies
- [x] 3.3 Review CSRF adjacency for cookie-authenticated session (refresh/logout today; full API after migration) given CORS + SameSite
- [x] 3.4 Finalize D9 cookie names, Path/Domain/SameSite/Secure, CSRF mechanism, and any non-browser Bearer compatibility path; document in `design.md`

## 4. Surface review — authorization and tenancy (C)

- [x] 4.1 Map role dependency matrix (`get_current_*`) to mutating/list routes; note any unauthenticated or under-guarded routes
- [x] 4.2 Probe cross-tenant IDOR candidates (users, orgs, events, appliances, articles, reports) beyond existing `security #3/#15` tests
- [x] 4.3 Verify platform-admin `X-Hire-Company-Id` scoping has no confused-deputy paths; record findings

## 5. Surface review — edge and Stripe Terminal (C, full depth)

- [x] 5.1 Review pairing code lifecycle (create, expiry, single use, rate limit) against `cloud-edge-security`
- [x] 5.2 Review edge credential verify, revoke/unpair, and org/event scoping for bundle/orders/sync
- [x] 5.3 Review Stripe webhook signature verification and idempotency/duplicate handling
- [x] 5.4 Deep-dive edge Stripe Terminal (connection token, create/read PaymentIntent, org/event scope, confused deputy)

## 6. Surface review — hosted-Pi (Critical secret boundary) and deploy/config (C)

- [x] 6.1 Review `HOSTED_PI_MANAGER_SECRET` gate, cloud-backend client, and that edge secrets only flow on authenticated provision (Critical)
- [x] 6.2 Skim hosted-Pi orchestrator internals (compose/network/slug) at Medium; promote findings if High/Critical
- [x] 6.3 Review XSS surfaces (`v-html`, markdown) and admin CSP in `cloud/Caddyfile`
- [x] 6.4 Review `docker-compose.prod.yml`, `.env.example`, CORS, OpenAPI, cookie Secure, single-container rate-limit assumption, API/admin headers

## 7. HttpOnly access-token migration (in scope)

- [x] 7.1 Add failing backend/frontend tests for HttpOnly access cookie, no `localStorage` access JWT, and CSRF/CORS mutation protections
- [x] 7.2 Implement backend cookie issuance and access-from-cookie auth (preserve refresh rotation / `token_version`)
- [x] 7.3 Update cloud frontend to stop storing access tokens; use credentialed requests end-to-end (login, refresh, logout, API client)
- [x] 7.4 Remove or gate JSON body access-token exposure for browser login if required by the finalized D9 design; document any BREAKING non-browser path

## 8. Specs and other regression gaps

- [x] 8.1 For each baseline/edge/session requirement, mark covered by existing tests vs gap in `findings.md`
- [x] 8.2 Add failing tests first for other Critical/High gaps (extend `security #N` numbering where practical)
- [x] 8.3 Update capability specs via `/opsx:update` if requirement text must tighten further (including `cloud-user-tenancy` deltas if needed)

## 9. Hardening Critical and High

- [x] 9.1 Implement fixes for Critical findings with tests green
- [x] 9.2 Implement fixes for High findings with tests green (or record accepted risk with owner in `findings.md`)
- [x] 9.3 Present Medium/Low list to Christoph for accept vs backlog; record decisions in `findings.md`

## 10. Verification

- [x] 10.1 Run cloud backend tests (`cd cloud/backend && uv run pytest`)
- [x] 10.2 Run cloud frontend tests and typecheck (auth/session changed)
- [x] 10.3 Run `./scripts/lint.sh` for touched areas
- [x] 10.4 Validate OpenSpec change (`npx openspec validate cloud-security-audit --strict`)
