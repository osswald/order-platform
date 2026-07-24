## Why

The cloud admin stack (frontend, backend, `/edge`, and production deploy/config) holds multi-tenant org data, session credentials, appliance pairing secrets, and Stripe payment surfaces. Prior hardening exists (JWT type separation, token-version rotation, tenancy isolation tests, PyJWT migration, Caddy headers), but there is no living threat model or systematic surface review that includes edge credentials and ops configuration. We need a structured audit now so findings become enforceable requirements and regression tests—not a one-off checklist that drifts.

## What Changes

- Produce a **threat model** for cloud admin + edge + deploy/config (actors, assets, trust boundaries, abuse cases).
- Run a **full surface review** against that model: auth/session, role/tenancy authorization, `/edge` pairing and credential lifecycle, Stripe webhook/Terminal boundaries, frontend XSS surfaces, and production Caddy/compose/env hardening.
- **Move admin access JWTs out of `localStorage`** into HttpOnly cookies (cookie-based session for the admin API), and harden CSRF posture for cookie-authenticated requests—**in this change**, not as a follow-on.
- Capture durable outcomes as OpenSpec capabilities (security baseline + edge security), extending the existing numbered `security #N` test coverage where gaps appear.
- Produce a severity-ranked **findings record** and a **hardening backlog**; implement Critical/High fixes in this change (tests first). Medium/Low acceptance is decided by the change owner.
- Explicitly treat frontend route/role guards as **UX only**; API and edge auth remain the security boundary under review.
- **Split depth**: full Critical review of edge Stripe Terminal; hosted-Pi manager reviewed as Critical for shared-secret auth / who can provision, with deeper orchestrator internals at Medium unless a High/Critical finding appears.

## Capabilities

### New Capabilities
- `cloud-security-baseline`: Cross-cutting cloud security properties for admin sessions (including HttpOnly access-token delivery), authorization boundaries, cookie/CORS/CSRF posture, password/secret policy, OpenAPI exposure, single-instance rate-limit assumptions, and production deploy/config (Caddy headers/CSP, compose/`APP_ENV`, required secrets).
- `cloud-edge-security`: Security properties for appliance pairing codes, edge client credentials, `/edge` API auth, unpair/revoke, privilege limits for order ingest and Stripe Terminal, and hosted-Pi manager shared-secret boundary.

### Modified Capabilities
- `cloud-session-jwt`: Require that access tokens used by the cloud admin UI are not readable by page JavaScript (`localStorage` / non-HttpOnly storage); document cookie delivery and CSRF expectations alongside existing HS256 / `typ` rules.
- `cloud-user-tenancy`: Extend only if the audit finds missing isolation requirements (e.g. incomplete IDOR matrix for a role). No change assumed until findings land.

## Impact

- **In scope**: `cloud/backend` (auth cookie issuance, CSRF/session, tenancy, routers including `/edge`, Stripe webhooks/Terminal, rate limits, config, hosted-Pi manager client), `cloud/frontend` (remove access-token `localStorage`, credentialed fetches, login/logout/refresh), `cloud/Caddyfile`, `cloud/docker-compose.prod.yml`, `cloud/.env.example`, related frontend nginx where relevant; light review of `cloud/hosted-pi-manager` secret gate.
- **Out of scope for this change**: Pi backend/frontend application logic except as a client of `/edge`; Android; non-cloud infrastructure outside the cloud compose/Caddy deploy path; Redis/shared rate-limit storage (prod is one container).
- **Artifacts**: Threat model + `findings.md`; new/updated specs; regression tests under `cloud/backend/tests/` and cloud frontend auth tests; hardening in the same change for Critical/High.
- **Possible BREAKING** client contract: admin UI and any external callers that read access tokens from JSON body / `localStorage` must switch to cookie credentials (document in apply).
