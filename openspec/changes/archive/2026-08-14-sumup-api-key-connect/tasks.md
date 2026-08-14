## 1. Backend credential resolution

- [x] 1.1 Add failing tests for `get_valid_access_token`: static API key (no refresh_token) returns credential without calling refresh; OAuth path with refresh_token still refreshes
- [x] 1.2 Implement API-key branch in `sumup_tokens.get_valid_access_token` and keep OAuth refresh when refresh_token is present
- [x] 1.3 Run cloud backend SumUp token/client tests

## 2. Backend API-key connect / update

- [x] 2.1 Add failing API tests for connect with valid key, reject invalid key, never echo key in status, connect without OAuth client env, update same merchant (readers preserved), update different merchant rejected, disconnect clears credentials and local readers
- [x] 2.2 Add connect/update API-key endpoint(s) on `sumup_connect` (validate via `/me`, persist merchant_code + access_token, clear refresh/expiry on API-key save)
- [x] 2.3 Ensure disconnect semantics unchanged; leave OAuth authorize/callback mounted
- [x] 2.4 Export OpenAPI and regenerate cloud frontend API types
- [x] 2.5 Run cloud backend SumUp connect tests

## 3. Cloud frontend SumUp-Geräte

- [x] 3.1 Add failing tests for `sumupCloud` helpers: connect/update API key calls; status mapping without OAuth authorize
- [x] 3.2 Replace OAuth connect CTA with API-key paste form; add update-key form when connected; keep disconnect
- [x] 3.3 Add payments-ready banner when Affiliate Key / platform checkout deps are missing (without blocking connect)
- [x] 3.4 Add/update i18n strings (de/en) for paste guidance, warnings, update, payments-not-ready
- [x] 3.5 Run cloud frontend tests and typecheck for touched files

## 4. Docs and verification

- [x] 4.1 Update `docs/sumup-cloud-api.md` for API-key primary connect and dormant OAuth
- [x] 4.2 Run targeted cloud backend + frontend SumUp tests and `./scripts/lint.sh` for touched areas
