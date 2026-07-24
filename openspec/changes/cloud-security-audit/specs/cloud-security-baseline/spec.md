## ADDED Requirements

### Requirement: Production secrets and OpenAPI exposure are constrained
When `APP_ENV` is `production`, the cloud backend SHALL refuse to start without a strong unique `SECRET_KEY` (not missing, not a known placeholder, and meeting the configured minimum length). Production deploy configuration and `.env.example` guidance SHALL set `ENABLE_OPENAPI` such that OpenAPI docs and schema are disabled unless explicitly enabled for a controlled environment. Non-production environments MAY enable OpenAPI.

#### Scenario: Production rejects weak SECRET_KEY
- **WHEN** the backend starts with `APP_ENV=production` and a missing, placeholder, or too-short `SECRET_KEY`
- **THEN** startup fails before serving requests

#### Scenario: OpenAPI disabled under production guidance
- **WHEN** production environment configuration from the documented deploy path is applied
- **THEN** OpenAPI UI and schema endpoints are not publicly enabled
- **AND** requests to docs/schema return non-success or are absent

### Requirement: Admin session cookies use secure browser flags
Access and refresh session cookies used by the cloud admin UI SHALL be `HttpOnly` and use `SameSite=Lax` (or stricter). When `REFRESH_COOKIE_SECURE` (or the equivalent access-cookie secure setting) is enabled for production HTTPS, those cookies SHALL also be marked `Secure`. Refresh tokens MUST NOT authenticate API requests that require an access token (see `cloud-session-jwt`).

#### Scenario: Session cookie flags on login
- **WHEN** a client successfully logs in via `POST /auth/token`
- **THEN** the response sets access and refresh cookies that are HttpOnly
- **AND** SameSite is Lax or stricter on those cookies
- **AND** if secure-cookie configuration is enabled, the Secure flag is set

### Requirement: Admin access tokens are not readable by page JavaScript
The cloud admin UI MUST NOT store access JWTs in `localStorage`, `sessionStorage`, or other script-readable storage. Access tokens for browser sessions SHALL be delivered only via HttpOnly cookies (see `cloud-session-jwt`). Role or UX flags MAY remain in local storage but MUST NOT grant API authorization.

#### Scenario: Login does not persist access token in localStorage
- **WHEN** the admin UI completes a successful login
- **THEN** no access JWT value is written to `localStorage` or `sessionStorage`
- **AND** subsequent authenticated API calls rely on credentialed cookies (and CSRF protections as required)

### Requirement: Cookie-authenticated admin mutations are CSRF-protected
When admin API authentication for browser clients is cookie-based, state-changing requests SHALL be protected against cross-site request forgery by the combination of CORS origin allowlisting, cookie SameSite policy, and any additional CSRF mechanism required by the implemented cookie design. Cross-site requests from origins not in `ALLOWED_ORIGINS` MUST NOT successfully mutate authenticated state.

#### Scenario: Disallowed origin cannot mutate with victim cookies
- **WHEN** a cross-site request from an origin not in `ALLOWED_ORIGINS` attempts a state-changing admin API call that would rely on ambient session cookies
- **THEN** the request does not succeed as an authenticated mutation

### Requirement: CORS credentials are origin-allowlisted
The cloud backend SHALL allow credentialed cross-origin requests only for origins listed in `ALLOWED_ORIGINS`. Wildcard reflection of arbitrary `Origin` values with credentials MUST NOT be enabled.

#### Scenario: Disallowed origin cannot use credentialed CORS
- **WHEN** a browser preflight or credentialed request presents an Origin not in `ALLOWED_ORIGINS`
- **THEN** the response does not grant CORS access for that origin with credentials

### Requirement: Login and refresh abuse are rate-limited
The cloud backend SHALL rate-limit login and refresh endpoints according to configured limits so that credential stuffing and refresh flooding are constrained per client key. Under the documented single cloud-backend container production topology, in-memory rate-limit storage is acceptable.

#### Scenario: Excess login attempts are rejected
- **WHEN** a client exceeds the configured login rate limit
- **THEN** subsequent login attempts receive HTTP 429

### Requirement: API authorization is authoritative over frontend guards
Cloud admin APIs SHALL enforce authentication and role/tenant authorization on the server. Presence or absence of frontend route meta or localStorage role flags MUST NOT grant access to data or mutating operations.

#### Scenario: Member session cannot perform tenant-admin-only API action
- **WHEN** a user with role `member` calls an API endpoint reserved for tenant or platform admins
- **THEN** the response is HTTP 401 or 403
- **AND** no privileged mutation occurs

### Requirement: Cross-tenant object access is denied
Authenticated non-platform actors MUST NOT read or mutate resources belonging to another HireCompany. Platform admins MAY act across hire companies only via the explicit active hire-company mechanism (`X-Hire-Company-Id` or equivalent documented selector); requests MUST remain scoped to that active hire company for list/detail operations covered by tenancy rules.

#### Scenario: Tenant admin cannot read another hire company's resource by id
- **WHEN** a `tenant_admin` of hire company A requests a resource id that belongs only to hire company B
- **THEN** the response is HTTP 404 or 403
- **AND** resource contents are not returned

### Requirement: Production edge headers protect the admin UI
Production Caddy (or equivalent edge) configuration for the admin UI host SHALL send HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`), and a Content-Security-Policy that does not allow `script-src` from arbitrary third-party hosts. The API host SHALL send the shared security headers (HSTS, nosniff, frame denial).

#### Scenario: Admin host CSP restricts scripts to self
- **WHEN** production Caddy admin site headers are inspected
- **THEN** a Content-Security-Policy is present
- **AND** `script-src` does not include arbitrary https: hosts or unsafe-eval

### Requirement: Password change rejects empty secrets
Changing a user password SHALL require a new password with length at least the configured minimum policy (baseline: greater than zero characters). The system MUST NOT accept an empty new password string.

#### Scenario: Empty new password rejected
- **WHEN** an authenticated user submits a password change with an empty new password
- **THEN** the request is rejected with a validation or client error
- **AND** the stored password hash is unchanged

### Requirement: Security regression tests remain mapped
Security-sensitive behaviors covered by this capability and by `cloud-session-jwt` / tenancy isolation SHALL remain covered by automated tests. Existing `security #N` anchors (JWT types, SECRET_KEY, session lifecycle, tenant IDOR) MUST continue to pass; new Critical/High audit fixes SHALL add or extend tests before code changes land.

#### Scenario: Known security anchors pass
- **WHEN** the cloud backend security-related test suite is run
- **THEN** JWT type separation, SECRET_KEY production rules, session rotation, and cross-tenant user isolation tests pass
