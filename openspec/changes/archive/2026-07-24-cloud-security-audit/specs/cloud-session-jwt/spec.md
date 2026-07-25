## ADDED Requirements

### Requirement: Browser admin access tokens are HttpOnly
For cloud admin browser sessions, access JWTs SHALL be issued in HttpOnly cookies and MUST NOT be required to be stored in script-readable web storage for the admin UI to call authenticated APIs. Access and refresh tokens remain type-separated (`typ` claim); a refresh token MUST NOT authorize endpoints that require an access token.

#### Scenario: Access token not exposed to document.cookie for HttpOnly cookie
- **WHEN** a browser client completes login and receives the access session cookie
- **THEN** the access cookie is marked HttpOnly
- **AND** the admin UI can call authenticated APIs using credentialed requests without reading the access JWT from JavaScript storage

#### Scenario: Refresh still cannot call access-protected API
- **WHEN** a client presents only a refresh token where an access token is required
- **THEN** the response is HTTP 401
