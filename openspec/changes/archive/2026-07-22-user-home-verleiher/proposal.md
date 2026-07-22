## Why

Creating a member or organisation-admin without organisations makes them disappear from every user list: create/sync clears `hire_company_id`, and listing only includes users with a Verleiher anchor via HC or org links. Admins then cannot find or recover those users through the UI.

## What Changes

- Treat `User.hire_company_id` as **home Verleiher** for `member` and `organisation_admin` (not only for `tenant_admin`).
- On create under an active Verleiher, set `hire_company_id` to that Verleiher for members and organisation-admins, even when `organisation_ids` is empty.
- Stop clearing `hire_company_id` in role sync for those roles; keep it when clearing all organisations or demoting from `tenant_admin`.
- Keep `platform_admin` with `hire_company_id = null` (cross-tenant).
- Organisation-admins creating users still require ≥1 organisation (unchanged).
- No global unscoped user directory for platform-admins; visibility remains scoped to the active Verleiher.
- **Backfill** existing `member` / `organisation_admin` rows with null `hire_company_id` from a single unambiguous organisation Verleiher (startup schema patch + Alembic). True orphans (no orgs) and ambiguous multi-Verleiher links remain unchanged.

## Capabilities

### New Capabilities

- `cloud-user-tenancy`: Home-Verleiher membership and role-scoped user visibility for cloud user management (platform / Verleiher / organisation admins).

### Modified Capabilities

- (none)

## Impact

- Cloud backend: `app/routers/users.py`, `app/tenancy.py`, `app/database.py` backfill, Alembic `007_backfill_user_home_verleiher`; tests for list/create/isolation/backfill.
- Cloud frontend: no required UI change if API returns org-less users; optional copy/hint may clarify “unassigned” users stay under the Verleiher.
- Existing users with orgs and null HC: backfilled on deploy/startup. True orphans (no orgs) remain for manual recovery.
- Permissions unchanged: role gates admin power; setting HC on members/org-admins does not grant Verleiher-admin rights.
