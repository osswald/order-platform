## Context

See proposal.md — Why. Organisations already store SumUp credentials on `Organisation` (`sumup_merchant_code`, `sumup_access_token`, `sumup_refresh_token`, `sumup_token_expires_at`). Readers, edge checkout, and Affiliate Key attachment already use `get_valid_access_token` + `Authorization: Bearer`. The gap is connect: UI and specs assume OAuth, while SumUp withholds the OAuth `payments` scope.

## Goals / Non-Goals

**Goals:**

- Primary connect via merchant API key with `/me` validation.
- Token resolution supports API-key credentials without refresh.
- Rotate key without wiping readers when merchant matches.
- Keep OAuth routes/client usable but not offered in SumUp-Geräte.
- Platform “payments ready” tied to Affiliate Key, not OAuth client env.

**Non-Goals:**

- Encryption-at-rest for stored keys (same bar as current OAuth tokens).
- Exposing `auth_mode` on status APIs in this change.
- Reviving OAuth in the UI or requesting `payments` scope activation as part of this work.
- Changing Pi edge checkout contracts or Solo reader pairing UX beyond connect.
- Per-hire-company or platform-shared API keys (credentials remain organisation-scoped).

## Decisions

1. **Reuse `sumup_access_token` for the API key**  
   Store the merchant API key in `sumup_access_token`. Leave `sumup_refresh_token` and `sumup_token_expires_at` null. Infer mode: refresh token present → OAuth refresh path; else treat access token as static API key.  
   **Alternatives considered:** Dedicated `sumup_api_key` column + `auth_mode` enum — clearer, more migration. Deferred; inference is enough while OAuth is dormant and status does not expose mode.

2. **New connect/update endpoints; leave OAuth endpoints mounted but unused by UI**  
   - `POST /sumup/organisations/{id}/api-key` (or equivalent) accepts the key, validates via SumUp `/me`, sets merchant_code + access_token, clears refresh/expiry, sets `sumup_connected_at`.  
   - Same endpoint (or PATCH) while connected: replace key if `/me` merchant_code matches existing; reject mismatch.  
   - Keep `/authorize` and `/oauth/callback` for dormant OAuth; SumUp-Geräte must not call them.  
   **Alternatives considered:** Replace OAuth routes entirely — rejected so reactivation is cheap. Hybrid UI (both CTAs) — rejected to avoid confusion while `payments` is blocked.

3. **Never return the secret**  
   Status and all list/detail responses omit the key. UI shows connected + merchant_code + reader_count only. Update form is write-only (empty field, paste new key).

4. **Disconnect vs update**  
   Disconnect clears merchant linkage, tokens, and local `sumup_readers` (unchanged semantics). Update replaces credential only. Historical payments untouched in both cases.

5. **Platform configured / payments ready**  
   - API-key connect MUST NOT require `SUMUP_CLIENT_ID` / `SECRET` / redirect.  
   - Solo checkout continues to require Affiliate Key (existing client behaviour).  
   - Frontend “not configured” for the devices page SHOULD mean the deployment cannot take Solo payments (missing Affiliate), not missing OAuth client. Connecting may still be allowed so orgs can pair readers before Affiliate is set, with a clear banner when payments are not ready.  
   **Alternatives considered:** Hard-block connect without Affiliate — stricter fail-early; softer banner preferred so pairing/setup can proceed in staging.

6. **Validation**  
   On connect/update, list SumUp memberships for the key (API keys often span live + sandboxes). Do **not** use `/me` alone for merchant identity — it returns the default live merchant. If multiple memberships exist, require `merchant_code` selection (409 with merchant list). On update, keep the stored merchant and verify the key still has access to it.

## Risks / Trade-offs

- **[Risk] API keys are broad merchant secrets** → Mitigation: org-admin-only APIs (existing ACL); never echo key; short UI warning that the key grants full SumUp API access for that merchant.
- **[Risk] Key shown once in SumUp dashboard — users lose it** → Mitigation: document “create a new key and use Update”; rotate path avoids re-pairing.
- **[Risk] Stale OAuth orgs if any exist in DB** → Mitigation: token helper still refreshes when refresh_token present; UI only offers API key going forward (admins can disconnect and reconnect with a key).
- **[Risk] Affiliate missing → connect OK, pay fails at event** → Mitigation: payments-ready banner on SumUp-Geräte; checkout errors remain explicit.
- **[Trade-off] Inferring auth mode from refresh_token nullability** → Slightly opaque vs explicit column; acceptable while mode is not exposed.

## Migration Plan

1. Deploy backend endpoints + token helper behaviour (backward compatible for existing OAuth rows).
2. Ship frontend SumUp-Geräte paste/update UI; stop offering OAuth CTA.
3. Ops: ensure `SUMUP_AFFILIATE_KEY` (+ app id) set for production checkout; OAuth env optional.
4. Orgs: create API key in me.sumup.com → paste into SumUp-Geräte → pair readers as today.
5. Rollback: re-enable OAuth CTA only if SumUp has activated `payments`; API-key rows remain valid Bearers.

## Open Questions

- None blocking implementation; Affiliate banner copy/i18n can be finalized during apply.
