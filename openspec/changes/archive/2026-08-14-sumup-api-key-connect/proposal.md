## Why

SumUp gates the OAuth `payments` scope behind manual app verification, which blocks Solo Cloud API checkouts for organisations that connect via OAuth. Merchant API keys authorize the same Cloud API (including reader checkout) without that scope gate. We need a primary connect path that unblocks card payments while SumUp OAuth approval remains pending.

## What Changes

- Make **per-organisation SumUp API key paste** the primary connect path on **SumUp-Geräte**.
- On connect and on key update: validate the key with SumUp (`/me`), persist merchant identity + credential on the organisation, never echo the key back in APIs or UI.
- Allow **updating the API key** while connected without deleting paired readers, when the key belongs to the same merchant.
- Keep **disconnect** as the full teardown (clear credentials, local readers, connection state).
- Keep **OAuth authorize/callback/token refresh code dormant** (not offered in UI; available when SumUp activates `payments`).
- Treat platform “payments ready” as presence of Affiliate Key (and related checkout deps), not OAuth client credentials.
- Update docs to describe API-key connect; OAuth remains documented as dormant/future.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `sumup-cloud-connect`: Primary connect becomes API key paste; OAuth is no longer the primary (or UI-offered) path; add key update without reader wipe; clarify disconnect vs rotate; redefine when the admin surface considers SumUp usable on the server. Edge checkout and payment-type behaviour stay under `sumup-cloud-payments` and are unchanged aside from resolving the organisation Bearer credential (API key or dormant OAuth token).

## Impact

- Cloud backend: `sumup_connect` router (new connect/update API-key endpoints), `sumup_tokens.get_valid_access_token` (API-key mode without refresh), status/`configured` semantics, OpenAPI export + frontend types.
- Cloud frontend: `SumupDevices.vue` connect UX (paste + update key); hide OAuth CTA; `sumupCloud.ts` helpers/tests.
- Docs: `docs/sumup-cloud-api.md`, help/i18n copy for SumUp-Geräte.
- Env: `SUMUP_AFFILIATE_KEY` (and app id) remain required for live Solo checkout; `SUMUP_CLIENT_ID` / `SECRET` / redirect optional while OAuth is dormant.
- Pi / edge checkout routes: unchanged call shape; continue to use organisation Bearer credential + Affiliate metadata.
