## Why

Dependabot alert [#51](https://github.com/osswald/order-platform/security/dependabot/51) flags transitive `ecdsa` (GHSA-wj6h-64fc-37mp / CVE-2024-23342) in `cloud/backend/uv.lock`. The package is pulled in solely by `python-jose`, has **no planned upstream fix**, and is unused for our HS256-only session JWTs. Migrating to PyJWT removes the vulnerable dependency from the tree instead of dismissing the alert forever.

## What Changes

- Replace `python-jose[cryptography]` with `PyJWT` in `cloud/backend/pyproject.toml` and regenerate `uv.lock`.
- Update `cloud/backend/app/security.py` and JWT tests to use PyJWT (`jwt` / `PyJWTError`).
- Keep session JWT behaviour unchanged: HS256, `typ` access/refresh separation, existing claim shape and cookie/bearer flows.
- After merge, Dependabot alert #51 SHOULD clear (or be dismissable as fixed). Optionally delete the stale pre-uv `cloud/backend/requirements.lock` if it still lists `ecdsa` and is unused.

## Capabilities

### New Capabilities
- `cloud-session-jwt`: Cloud admin session tokens are HS256 JWTs issued and verified via PyJWT; access and refresh tokens remain distinguished by `typ` and MUST NOT accept each other.

### Modified Capabilities
- (none — dependency swap does not change `python-dependency-management` or `dependency-maintenance` requirements)

## Impact

- **Code**: `cloud/backend/app/security.py`, `cloud/backend/tests/test_jwt_token_types.py` (and any other `from jose` imports if introduced later — none elsewhere today).
- **Callers unchanged**: `auth.py`, `auth_deps.py`, and edge pairing (pairing codes + hashed edge secrets, not JWT) stay as-is.
- **Dependencies**: drop `python-jose`, `ecdsa`, `rsa`, `pyasn1`, and the jose-only `cryptography` extra from the cloud backend lockfile (unless another direct dep reintroduces them).
- **Pi backend / frontends**: not affected.
- **Tokens in the wild**: HS256 tokens remain compatible if claim encoding stays equivalent; no forced logout expected beyond normal expiry.
- **No VERSION bump** in the feature PR; use a release label if a release is desired.
