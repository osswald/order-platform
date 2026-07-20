# cloud-session-jwt Specification

## Purpose
Define how the cloud backend issues and verifies admin session JWTs (access and refresh), including algorithm and library constraints that keep unneeded crypto dependencies out of the lockfile.

## Requirements
### Requirement: Cloud session JWTs use HS256 via PyJWT
The cloud backend SHALL issue and verify admin session JWTs (access and refresh) using the **PyJWT** library with algorithm **HS256** and the configured `SECRET_KEY`. The cloud backend MUST NOT depend on `python-jose` or `ecdsa` for session tokens.

#### Scenario: Dependency tree excludes ecdsa
- **WHEN** `uv.lock` for `cloud/backend` is inspected after dependency resolution
- **THEN** packages `python-jose` and `ecdsa` are not present
- **AND** `PyJWT` is present as a direct dependency

#### Scenario: Access token round-trip
- **WHEN** an access token is created for a user subject
- **THEN** it can be decoded as an access token with the same subject and `typ` equal to access
- **AND** the JWT header algorithm is `HS256`

### Requirement: Access and refresh tokens remain type-separated
Access and refresh JWTs SHALL carry a `typ` claim that distinguishes them. Decoding a refresh token as an access token (or vice versa) MUST fail. A refresh token MUST NOT authenticate Bearer API requests that require an access token.

#### Scenario: Refresh rejected as access
- **WHEN** a refresh token is passed to access-token decode
- **THEN** decoding fails

#### Scenario: Access rejected as refresh
- **WHEN** an access token is passed to refresh-token decode
- **THEN** decoding fails

#### Scenario: Refresh cannot call authenticated API as Bearer
- **WHEN** a client calls an authenticated endpoint with `Authorization: Bearer <refresh_token>`
- **THEN** the response is HTTP 401
