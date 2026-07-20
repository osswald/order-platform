## 1. Tests first

- [x] 1.1 Extend `cloud/backend/tests/test_jwt_token_types.py` to assert HS256 in the JWT header and import JWT errors from the post-migration API (or a stable alias in `app.security`)
- [x] 1.2 Confirm existing typ-separation and refresh-as-Bearer 401 scenarios still cover the `cloud-session-jwt` spec

## 2. Dependency swap

- [x] 2.1 Branch from `main` for this change
- [x] 2.2 Replace `python-jose[cryptography]` with `PyJWT` in `cloud/backend` via `uv` (`uv remove` / `uv add`); commit `pyproject.toml` + `uv.lock` together
- [x] 2.3 Verify `uv tree` (or lockfile) has no `ecdsa` / `python-jose`
- [x] 2.4 Confirm nothing in Docker/CI references `cloud/backend/requirements.lock`; if unused, delete the stale file

## 3. Code migration

- [x] 3.1 Update `cloud/backend/app/security.py` to encode/decode with PyJWT while keeping helper signatures and HS256
- [x] 3.2 Ensure JWT failure paths still surface as auth failures (401) for invalid/wrong-type tokens

## 4. Verify

- [x] 4.1 Run cloud backend tests (`cd cloud/backend && uv sync && uv run python -m pytest tests/ -v`)
- [x] 4.2 Run `./scripts/lint.sh` (or staged) for touched Python files
- [x] 4.3 Note in PR that Dependabot alert #51 should be confirmed after merge (cannot verify pre-merge)
