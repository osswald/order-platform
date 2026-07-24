# Cloud security audit — findings

**Change:** `cloud-security-audit`  
**Owner (Medium/Low accept):** Christoph  
**Assumptions:** D5 HttpOnly access in scope · D7 single-container `memory://` OK · D8 Terminal full / hosted-Pi secret Critical · D4 owner accepts Medium/Low  
**Owner decisions recorded:** 2026-07-24

## Assumptions log

| Decision | Record |
|----------|--------|
| D5 | Access JWT must leave `localStorage`; HttpOnly cookie + CSRF in this change |
| D7 | Prod = one `cloud-backend` container; in-memory rate limits acceptable |
| D8 | Terminal = Critical deep-dive; hosted-Pi orchestrator internals = Medium |
| D4 | Christoph decides each Medium/Low accept vs backlog |
| D9 | Finalized in `design.md` (host-only cookies, Origin CSRF, Bearer for tests) |

## Findings

| ID | Sev | Surface | Title | Status |
|----|-----|---------|-------|--------|
| F1 | High | auth | Access JWT in `localStorage` | **Fixed** — HttpOnly `access_token` cookie; FE uses `auth_session` UX flag |
| F2 | High | auth | Same-site subdomain CSRF once cookies auth API | **Fixed** — `CookieCsrfMiddleware` Origin/Referer allowlist |
| F3 | High | deploy | OpenAPI defaults on if unset | **Fixed** — prod default off + compose `ENABLE_OPENAPI=false` |
| F4 | High | stripe | Client-controlled Connect return/refresh URLs | **Fixed** — env-only URLs |
| F5 | Medium | terminal | Client metadata can overwrite PaymentIntent system keys | **Fixed** — system keys applied last |
| F6 | Medium | terminal | GET PaymentIntent not bound to event_id metadata | **Fixed** + tests |
| F7 | Medium | auth | Password policy ≈ non-empty | **Backlog** — stronger min length / complexity |
| F8 | Medium | deploy | `REFRESH_COOKIE_SECURE` defaults false | **Fixed** — Secure forced when `APP_ENV=production`; compose sets true |
| F9 | Medium | deploy | Rate limits key on peer (Caddy), not client IP | **Backlog** — trusted `X-Forwarded-For` from Caddy (or equivalent) |
| F10 | Medium | edge | Pairing verifies against all active sessions (CPU) | **Accepted** — OK at current pairing scale |
| F11 | Medium | tenancy | Waiter PINs returned in API / default `0000` | **Accepted** — venue PIN model |
| F12 | Medium | hosted-pi | Docker socket + edge secrets on disk | **Accepted** — orchestration model; protect host + manager secret |
| F13 | Info | hosted-pi | Manager secret gate present | Keep; empty secret rejects |
| F14 | Medium | auth | Refresh/logout CSRF can kill sessions | **Fixed** — folded into Origin CSRF |
| F15 | Medium | deploy | Bootstrap `ADMIN_PASSWORD` no strength check | **Accepted** — ops / secrets hygiene |
| F16 | Low | tenancy | Broad member write within linked orgs | **Accepted** — members are trusted org operators |
| F17 | Low | xss | Help `v-html` (static MD, html:false) | **Accepted** — static bundled content only |
| F18 | Low | deploy | CSP `style-src 'unsafe-inline'` | **Accepted** — Vuetify / admin UI |
| F19 | Low | hosted-pi | Manager secret `!=` timing | **Backlog** — `hmac.compare_digest` |
| F20 | Medium | terminal | Compromised edge can create arbitrary-amount PIs | **Accepted** — POS model; revoke/unpair mitigates |
| F21 | Info | stripe | Webhooks signature + idempotency OK | No action |
| F22 | Info | edge | Pairing lifecycle controls present | Tests added for Terminal foreign-event; EDGE_PAIR 429 still optional |

## Owner decision summary (task 9.3)

| Disposition | IDs |
|-------------|-----|
| **Backlog** (follow-on work) | F7, F9, F19 |
| **Accepted** residual risk | F10, F11, F12, F15, F16, F17, F18, F20 |

Suggested follow-on change names (optional): `password-policy`, `rate-limit-forwarded-for`, `hosted-pi-compare-digest`.

## Spec coverage matrix (task 8.1)

| Requirement area | Covered by tests? | Gap |
|------------------|-------------------|-----|
| JWT typ separation | Yes `#2` | — |
| SECRET_KEY prod | Yes `#4` | — |
| Session rotation | Yes `#9` | — |
| Tenant user IDOR | Yes `#3/#15` | Broader resource matrix still thin (Low/Info) |
| HttpOnly access / cookie auth | Yes `#16` | — |
| CSRF / Origin on cookie auth | Yes `#16` | — |
| OpenAPI prod fail-closed | Yes | — |
| Edge pair / revoke | Yes pairing tests | EDGE_PAIR 429 optional |
| Terminal foreign-event / metadata | Yes | — |
| Stripe webhook sig | Yes | — |
| Connect URL env-only | Yes | — |
| Hosted-Pi manager secret | Code review | Manager unit test optional |

## Inventory (summary)

**Public:** `/health`, `/auth/token|refresh|logout`, `/edge/v1/pair`, `/stripe/webhooks`, OpenAPI if enabled.  
**Admin:** access via Bearer **or** HttpOnly cookie + Origin CSRF on mutations; role/tenant deps.  
**Edge:** pair public; rest `X-Edge-Client-Id`/`X-Edge-Secret`.  
**Hosted-Pi manager:** `X-Manager-Secret` (internal).
