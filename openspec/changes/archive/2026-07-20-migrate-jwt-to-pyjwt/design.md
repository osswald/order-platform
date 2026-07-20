## Context

Dependabot alert [#51](https://github.com/osswald/order-platform/security/dependabot/51) reports **GHSA-wj6h-64fc-37mp** / **CVE-2024-23342** (Minerva timing attack on P-256) against transitive package `ecdsa` in `cloud/backend/uv.lock`. Severity is High (CVSS 7.4) but attack complexity is High. Upstream `python-ecdsa` treats side-channel attacks as out of scope; **vulnerable range is `>= 0` with no patched version**.

### Usage audit (what actually touches this)

```
cloud/backend
├── python-jose[cryptography] ──► ecdsa (hard dep) ◄── ONLY path to ecdsa
│                              ──► rsa, pyasn1
│                              ──► cryptography (extra)
├── app/security.py            ──► jose.jwt encode/decode, ALGORITHM=HS256
├── tests/test_jwt_token_types.py ──► jose.JWTError
└── callers: auth.py, auth_deps.py (via security helpers only)

NOT using jose / ecdsa:
├── Edge pairing / edge credentials ── secrets.token_urlsafe + password hash
├── Stripe webhooks / Terminal     ── Stripe SDK signatures
├── Pi backend                     ── no jose / ecdsa in lockfile
└── Frontends                      ── treat JWTs as opaque bearer strings
```

Conclusion: **nothing in the monorepo exercises ECDSA signing or ES* JWT algorithms.** The alert is lockfile noise for our HS256 path, but it will never clear via a version bump.

## Goals / Non-Goals

**Goals:**
- Remove `ecdsa` (and `python-jose`) from the cloud backend dependency tree.
- Preserve existing session JWT behaviour (HS256, `typ` access/refresh, claim shape, cookie refresh flow).
- Clear Dependabot alert #51 by fixing the tree, not by forever-dismissing.

**Non-Goals:**
- Changing algorithm to RS256/ES256 or introducing asymmetric keys.
- Reworking auth session model (`token_version`, refresh cookies, role claims).
- Migrating Pi or shared packages (they do not use jose).
- Dismissing the alert without a code/dependency change (kept as a documented alternative only).

## Decisions

### 1. Replace `python-jose` with PyJWT (not dismiss)

| | **Dismiss alert** | **Migrate to PyJWT** (chosen) |
|--|-------------------|-------------------------------|
| Effort | Minutes | Small (2 files + lock) |
| Clears Dependabot | Yes (as dismissed) | Yes (package gone) |
| `ecdsa` still installed | Yes | No |
| Future ES* footgun | Still present in tree | Absent unless we add it deliberately |
| Audit / compliance story | “Accepted risk” forever | “Removed unused vulnerable dep” |
| Upstream fix available | Never | N/A |

**Rationale:** Dismiss is honest about *current* risk but leaves a dead crypto library and permanent scanner debt. Migration cost is low and matches common FastAPI practice.

### 2. Depend on plain `PyJWT` (no `[crypto]` extra)

- We only need HS256 (HMAC). PyJWT’s crypto extra pulls `cryptography` for RSA/EC algorithms we do not use.
- Dropping jose’s `[cryptography]` extra also removes unused `cryptography` / `cffi` unless another direct dep reintroduces them (today nothing else declares `cryptography`).

### 3. Keep the public helpers in `app/security.py`

Call sites continue to use `create_*_token` / `decode_*_token` and catch JWT errors via whatever exception `security` re-exports or raises. Prefer mapping PyJWT’s `jwt.PyJWTError` (or subclass) so tests and any future callers stay stable; avoid leaking library-specific exception types into routers if easy to keep a thin alias.

### 4. Token wire compatibility

- Continue `ALGORITHM = "HS256"` and the same payload fields (`sub`, `exp`, `typ`, `token_version`, etc.).
- PyJWT and python-jose both emit compact JWTs; existing refresh cookies SHOULD remain valid across deploy (no forced mass logout), assuming claim encoding stays equivalent (datetime → numeric `exp`).

### 5. Stale `requirements.lock`

`cloud/backend/requirements.lock` is a pre-uv pip-compile artifact that still mentions `ecdsa` / `python-jose`. Specs require `uv.lock` as the source of truth. **Delete it in this change** if nothing in Docker/CI still references it (verify before delete); otherwise leave a follow-up task.

## Pros and cons of the migration

**Pros**
- Permanently removes unpatchable `ecdsa` and clears alert #51 for real.
- Shrinks the auth dependency surface (`ecdsa`, `rsa`, `pyasn1`, jose, likely `cryptography`).
- PyJWT is actively maintained and the usual FastAPI/Starlette recommendation for HS* JWTs.
- Tiny blast radius: one module + one focused test file; auth HTTP API unchanged.
- Avoids “dismiss forever” documentation debt on a High severity CVE.

**Cons / costs**
- One-time migration and review (API differences: import path, exception type, `jwt.encode` return type is `str` in modern PyJWT).
- Must re-verify encode/decode edge cases (`typ` mismatch, expired tokens, refresh-as-bearer) under PyJWT defaults (e.g. `require` / leeway — keep defaults aligned with current behaviour).
- If we later need ES*/RS* JWTs, we add `PyJWT[crypto]` + key management deliberately (today we do not need that).
- Slightly more churn than dismissing the alert (acceptable given scope).

## Risks / Trade-offs

- **[Risk] Subtle encode/decode differences invalidate refresh cookies** → Mitigation: keep HS256 + same claims; run existing JWT + auth integration tests; smoke login/refresh locally or in CI.
- **[Risk] Exception type change breaks tests or error handling** → Mitigation: update `test_jwt_token_types.py`; routers already catch broadly via `security` helpers / HTTP 401 paths.
- **[Risk] Stale `requirements.lock` keeps confusing scanners** → Mitigation: delete if unused, or confirm Dependabot only watches `uv` ecosystem paths.
- **[Risk] Someone enables ES256 later without noticing crypto needs** → Mitigation: spec locks algorithm to HS256; any algorithm change is a new OpenSpec change.

## Migration Plan

1. Branch from `main`; extend JWT tests to assert HS256 header and still cover typ separation (tests first).
2. Swap dependency with `uv remove python-jose` / `uv add PyJWT`; confirm `uv tree` has no `ecdsa`.
3. Update `security.py` imports and encode/decode; keep helper signatures.
4. Run cloud backend pytest, lint; open PR (no `VERSION` bump).
5. After merge, confirm Dependabot #51 auto-closes or dismiss as fixed.

**Rollback:** Revert the PR; restore `python-jose[cryptography]`. Tokens remain HS256 either way.

## Open Questions

- None blocking. Optional: pin a minimum PyJWT major (e.g. `PyJWT>=2.8,<3`) vs leave unconstrained like many other deps — prefer a modest lower bound consistent with repo style when applying.
