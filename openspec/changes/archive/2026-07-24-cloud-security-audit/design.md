## Context

Cloud admin auth today: OAuth2 password login → access JWT (Bearer, frontend `localStorage`) + refresh JWT (HttpOnly cookie). Authorization is role-based (`platform_admin` / `tenant_admin` / `organisation_admin` / `member`) with HireCompany tenancy via `X-Hire-Company-Id` for platform admins. Edge appliances authenticate with pairing codes then long-lived `X-Edge-Client-Id` / `X-Edge-Secret`. Stripe webhooks use signature verification; Terminal flows ride edge credentials. Production edge: Caddy (`admin.vendiqo.ch` with CSP, `api.vendiqo.ch` with security headers), `docker-compose.prod.yml` with `APP_ENV=production`.

Existing regression anchors: JWT type separation (`security #2`), tenant IDOR (`#3`, `#15`), SECRET_KEY (`#4`), session rotation (`#9`), plus role, OpenAPI, appliance pairing, and Stripe webhook tests. There is no living threat model and no single capability that covers edge credential security or deploy/config posture.

Stakeholders: operators of multi-tenant events, Verleiher/org admins, platform operators, and edge/Pi devices that ingest orders and take card payments. Change owner (Christoph) accepts or defers Medium/Low residual risk.

## Goals / Non-Goals

**Goals:**
- Document a threat model (actors, assets, trust boundaries, abuse cases) for cloud FE/BE + `/edge` + deploy/config.
- Systematically review those surfaces and record severity-ranked findings.
- Encode durable security properties as OpenSpec capabilities (`cloud-security-baseline`, `cloud-edge-security`) with testable scenarios.
- **Migrate admin access JWTs out of JavaScript-readable storage** to HttpOnly cookies in this change, with CSRF posture appropriate for cookie-authenticated API calls.
- Close gaps with tests-first hardening for Critical/High findings; Medium/Low become an explicit backlog with owner acceptance.
- Align with and extend the existing `security #N` test numbering where practical.

**Non-Goals:**
- Full penetration test of production (no live attack against prod without separate authorization).
- Pi application security beyond its role as an `/edge` client.
- Android / Play Store credential review (separate capability).
- Introducing Redis or shared rate-limit storage (production runs a single cloud-backend container; `memory://` is acceptable under that assumption).
- Deep rewrite of hosted-Pi orchestrator internals unless review surfaces High/Critical issues.
- Compliance certification (SOC2/ISO) evidence packages.

## Decisions

### D1 — Audit method: threat model (B) then surface review (C)
**Choice:** Write the threat model first in this design (and refine during apply), then walk each trust boundary with concrete probes (code review + targeted tests), not a generic OWASP dump.
**Why:** Highest leverage for this codebase; avoids reinventing controls already covered by `security #N` tests.
**Alternatives:** Checklist-only audit (shallow); external pen-test first (expensive before internal map); diff-only Security Review subagent (good for PRs, insufficient for full surface).

### D2 — Scope includes `/edge` and deploy/config
**Choice:** Treat edge pairing/credentials and Caddy/compose/env as first-class audit surfaces, equal to admin JWT/tenancy.
**Why:** Compromised edge credentials unlock order ingest and Stripe Terminal; misconfigured prod env undoes app-level controls.
**Alternatives:** App-code-only (rejected — leaves money path and ops blind spots).

### D3 — Specs describe the baseline we will verify and enforce
**Choice:** New capabilities state normative SHALL requirements for properties we intend to hold. Audit may tighten via `/opsx:update`; `cloud-session-jwt` is updated now for HttpOnly access delivery.
**Why:** Specs stay testable; archive yields living security docs instead of a stale PDF.
**Alternatives:** Findings-only markdown with no specs (drifts); over-specify unrelated remediations before audit (premature).

### D4 — Findings severity and remediation gating
**Choice:** Severity Critical / High / Medium / Low / Informational. Critical + High must get tests + fix (or documented accepted risk with owner) before this change is considered complete. Medium/Low may ship as backlog; **Christoph decides** acceptance vs deferral for each Medium/Low item.
**Why:** Keeps the change shippable without boiling the ocean; clear acceptance owner.
**Alternatives:** Fix everything in one PR (too large); audit-only with zero fixes (leaves known holes open).

### D5 — Frontend is attack surface; access token must not be JS-readable
**Choice:** Keep Vue role metas as UX-only. **In this change**, stop storing access JWTs in `localStorage` (or any non-HttpOnly storage). Deliver access tokens as HttpOnly cookies (alongside refresh), use `credentials: 'include'` for admin API calls, and add CSRF protections appropriate for cookie-authenticated mutating requests (at minimum preserve/strengthen SameSite + origin checks; add explicit CSRF token if cookie-only auth makes classic CSRF material).
**Why:** XSS must not yield a stealable Bearer token; user chose in-scope-now over residual risk.
**Alternatives considered:** Accept localStorage + CSP only (rejected); BFF that never issues tokens to the browser (heavier; defer unless cookie approach proves insufficient).

### D6 — Deliverable layout inside the change
**Choice:** Keep threat model and method in `design.md`; maintain a `findings.md` during apply (severity table + evidence paths); tasks drive review passes then hardening.
**Why:** OpenSpec-friendly; findings stay next to the change until archive.
**Alternatives:** External wiki only (easy to lose).

### D7 — Production rate limits: single container, `memory://` OK
**Choice:** Treat production as **one** `cloud-backend` container. Default `RATE_LIMIT_STORAGE_URI=memory://` is acceptable. Document the single-instance assumption; do not add Redis in this change. Revisit only if deploy topology changes.
**Why:** Confirmed by change owner; avoids false High on rate-limit storage.
**Alternatives:** Mandate Redis now (unnecessary for current topology).

### D8 — Split Terminal vs hosted-Pi review depth
**Choice:**
- **Edge Stripe Terminal**: full Critical-tier deep-dive (auth, org/event scoping, PaymentIntent/connection-token privilege).
- **Hosted-Pi manager**: Critical for `HOSTED_PI_MANAGER_SECRET` gate, who can call provision/destroy from cloud-backend, and that edge secrets are not exposed beyond the provision path; orchestrator internals (compose, network, slug) at Medium unless a High/Critical finding appears.
**Why:** Both money-adjacent but different trust boundaries; timebox without under-scoping card-present.
**Alternatives:** Same Critical tier for both (more time); defer Terminal (rejected for live card risk).

### D9 — Access-token cookie design (finalized in apply)
**Choice:**
| Item | Value |
|------|--------|
| Cookies | `access_token` + `refresh_token` (host-only on API; **no** `Domain=`) |
| Flags | `HttpOnly; SameSite=Lax; Secure` forced when `APP_ENV=production`, else `REFRESH_COOKIE_SECURE` |
| Path | `/` for both |
| JSON body | Still returns `access_token` for non-browser / TestClient **Bearer** clients |
| Browser UI | Must **not** store access JWT; uses `credentials: 'include'` only |
| Auth deps | Accept `Authorization: Bearer` **or** `access_token` cookie (Bearer preferred if both) |
| CSRF | Fail-closed **Origin** (else Referer) allowlist vs `ALLOWED_ORIGINS` on mutating methods when ambient cookies are present and Bearer is absent; exempt `/health`, `/edge/*`, `/stripe/webhooks` |
| Why Origin | `*.demo.vendiqo.ch` hosted Pi shares eTLD+1 with `api.vendiqo.ch`; SameSite alone is insufficient (F2) |

**Alternatives rejected:** SameSite-only CSRF; `Domain=.vendiqo.ch` (widens cookie scope).

## Threat model (initial)

### Assets
- Admin session JWTs (access + refresh) and `users.token_version`
- HireCompany / organisation / event / user PII and commercial data
- Edge pairing codes and edge client secrets
- Stripe secrets (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) and Terminal PaymentIntent capability
- `SECRET_KEY`, `HOSTED_PI_MANAGER_SECRET`, bootstrap admin credentials
- OpenAPI schema (reconnaissance) when enabled

### Actors
| Actor | Intent |
|-------|--------|
| External anonymous | Credential stuffing, pairing brute-force, webhook forgery, CORS/CSRF abuse |
| Authenticated member / org-admin | Privilege escalation, cross-tenant IDOR |
| Compromised browser (XSS) | Act as the user in-origin (cookies sent automatically); must **not** read access/refresh token values from JS |
| Stolen/mis-paired edge device | Order injection, Terminal abuse within lending org |
| Caller with leaked `HOSTED_PI_MANAGER_SECRET` | Provision hosted Pis and obtain edge credentials |
| Malicious or compromised platform admin | Out of band (trusted); note blast radius only |
| Insider with deploy access | Secret leakage, OpenAPI left on, weak cookie flags |

### Trust boundaries
```
[Browser] --cookies+CORS--> [Caddy admin/api] --> [cloud-backend]
[Pi/edge] --pair code / edge headers--> [/edge/v1/*]
[Stripe]  --signed webhook--> [/stripe/webhooks]
[cloud-backend] --X-Manager-Secret--> [hosted-pi-manager]
[Ops]     --env/secrets-----> [compose + Caddy]
```

### Priority abuse cases (review order)
1. Cross-tenant / cross-role IDOR on admin APIs
2. Edge pair brute-force, secret leakage, revoke/unpair gaps
3. Session cookies + CSRF after HttpOnly migration; XSS can no longer exfiltrate token strings
4. Edge Stripe Terminal confused deputy (full depth)
5. Hosted-Pi manager secret boundary (Critical); orchestrator internals (Medium)
6. Prod config: SECRET_KEY, OpenAPI, CORS, cookie Secure, single-instance rate limits, headers/CSP

## Risks / Trade-offs

- [Audit finds Critical issues mid-flight] → Gate merge of “audit complete” on fix or accepted-risk record; split remediations into follow-on PRs if large.
- [Specs over-claim current behavior] → Verify each scenario with failing/passing tests before archive; weaken or fix code, never leave false SHALL.
- [Cookie access token + cross-origin SPA] → CORS + SameSite + CSRF design must be tested carefully; risk of broken login or CSRF holes during migration.
- [BREAKING for Bearer-from-body clients] → Document migration; keep a narrow non-browser path only if explicitly required and tested.
- [Single-instance rate-limit assumption drifts] → Document in findings/baseline; revisit storage if replicas/workers are added.
- [No live prod pen-test] → Residual risk of env-only misconfig; mitigate with compose/Caddy review + `.env.example` contract tests where feasible.

## Migration Plan

1. Create feature branch from `main`; land planning artifacts (this change).
2. Apply phase: threat-model refinement → surface review passes → write `findings.md` → **HttpOnly access-token migration (tests first)** → other Critical/High hardening.
3. Update specs if requirements tighten; run cloud backend/frontend tests + lint.
4. Archive after merge; promote specs into `openspec/specs/`.
5. Rollback: hardening commits are independently revertable; cookie migration may need coordinated FE/BE revert.

## Open Questions

_None blocking._ Resolved as D5, D7, D8, D4 (owner). D9 finalized in apply.
