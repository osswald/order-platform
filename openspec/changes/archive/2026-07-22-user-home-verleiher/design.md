## Context

Cloud user listing (`GET /users/`) includes a user only if `hire_company_id` matches the active Verleiher **or** the user is linked to an organisation under that Verleiher. Today, create/update for `member` and `organisation_admin` forces `hire_company_id = None` via `_apply_role_on_create` and `sync_user_role_fields`. Empty `organisation_ids` therefore produces orphans that never appear in lists and fail tenant-scoped update/attach paths.

`user_belongs_to_tenant` and the list filter already treat `hire_company_id` as membership. Admin power is gated by **role** (`is_tenant_admin`), not by presence of HC. Platform-admin lists remain scoped by `X-Hire-Company-Id`.

## Goals / Non-Goals

**Goals:**

- Members and organisation-admins created under Verleiher V keep `hire_company_id = V` so they remain listable and manageable under V with zero organisations.
- Role sync / clearing orgs / demotion from `tenant_admin` must not strip home Verleiher for those roles.
- Cross-tenant isolation stays intact (users of Verleiher A never appear under Verleiher B).
- Org-admin actors still cannot create users without organisations.

**Non-Goals:**

- Global unscoped “all users on the platform” directory for platform-admins.
- Automatic repair of already-orphaned rows (null HC, no orgs).
- Changing organisation-admin list scope (they still only see users sharing an administered org).
- Frontend redesign beyond whatever already surfaces API results (optional hint only if needed).

## Decisions

### 1. `hire_company_id` = home Verleiher for member and organisation_admin

**Choice:** Persist the active tenant’s hire company id on create for `member` and `organisation_admin`; do not clear it in `sync_user_role_fields` for those roles.

**Why:** List and `user_belongs_to_tenant` already support this; no schema migration required. Permissions stay role-based.

**Alternatives considered:**

- Forbid empty orgs for members → rejects valid “parked / not yet assigned” workflow.
- Separate membership table → heavier than needed for this bug.
- Global platform user list → out of scope; product expectation is per-Verleiher.

### 2. Apply to organisation_admin as well as member

**Choice:** Same home-Verleiher rules for both roles.

**Why:** Same create path can orphan org-admins today; consistency avoids a second hole. Org-admins with zero orgs administer nothing but remain visible to Verleiher/platform admins for assignment.

### 3. Platform admin stays `hire_company_id = null`

**Choice:** Unchanged. Platform admins are not tenant-anchored.

**Why:** They resolve tenant via header; listing is always for the selected Verleiher.

### 4. Demotion and org clear preserve HC

**Choice:** When role changes from `tenant_admin` → `member` / `organisation_admin`, keep existing `hire_company_id` if it matches the current tenant (or set to current tenant). Clearing `organisation_ids` to `[]` must not null HC for these roles.

**Why:** Demotion/clear-orgs is how users become “unassigned” without disappearing.

### 5. Backfill existing users from organisation membership

**Choice:** On startup (`_backfill_user_home_verleiher`) and via Alembic `007_backfill_user_home_verleiher`, set `hire_company_id` for `member` / `organisation_admin` with null HC when all linked organisations share exactly one Verleiher. Skip platform admins, users with no orgs, and users linked across multiple Verleiher.

**Why:** Most legacy members already have orgs but null HC; deriving home Verleiher restores list visibility without inventing a tenant.

## Risks / Trade-offs

- [Semantic shift] Code or docs that assumed “HC set ⇒ tenant_admin” become wrong → Mitigation: rely on `role` / `is_tenant_admin`; audit call sites such as `user_hire_company_id` (today returns HC only for tenant_admins — leave as-is unless callers need home Verleiher for members).
- [Cross-tenant attach] Member with HC=A must still be rejectable when attaching to org under B → Mitigation: existing `ensure_users_in_tenant` / org hire_company checks; add/adjust tests.
- [True orphans] Users with null HC and no organisations remain invisible → Mitigation: noted in PR; rare after create-path fix.
- [Org-admin visibility] Org-less users still hidden from organisation-admins → Accepted; matches “see users of my organisations.”

## Migration Plan

1. Land tests for create/list behaviour and backfill, then implement create/sync/update + `_backfill_user_home_verleiher`.
2. Deploy backend (schema patch runs on startup; Alembic `007` for explicit upgrade history).
3. Rollback: revert code; backfilled HC values on members are harmless under the old list filter.

## Open Questions

- None blocking. Optional later: tooling for true orphans (null HC, no orgs).
