## 1. Tests first

- [x] 1.1 Add API tests: create `member` and `organisation_admin` with empty `organisation_ids` under Verleiher V → response and DB have `hire_company_id = V` and both appear in `GET /users/` for V
- [x] 1.2 Add API test: organisation-admin create with empty `organisation_ids` still returns organisation-required error
- [x] 1.3 Add API tests: update clearing `organisation_ids` to `[]` and demote `tenant_admin` → `member` / `organisation_admin` keep home Verleiher and remain listed
- [x] 1.4 Extend isolation tests: Verleiher-admin of B cannot update/delete/attach member with home Verleiher A and no orgs under B
- [x] 1.5 Add backfill tests: null-HC member/org-admin with single-Verleiher orgs get HC; orphans and multi-Verleiher skipped; idempotent

## 2. Backend create / sync / update

- [x] 2.1 Change `_apply_role_on_create` so `member` and `organisation_admin` set `hire_company_id` to the active tenant (not `None`)
- [x] 2.2 Change `sync_user_role_fields` so it does not clear `hire_company_id` for `member` / `organisation_admin` (platform_admin still clears; tenant_admin unchanged)
- [x] 2.3 Ensure update paths that clear organisations or change role preserve home Verleiher for those roles
- [x] 2.4 Audit callers of `user_hire_company_id` / assumptions that “HC set ⇒ tenant_admin”; adjust only if needed for correctness
- [x] 2.5 Add `_backfill_user_home_verleiher` schema patch + Alembic `007_backfill_user_home_verleiher`

## 3. Verify

- [x] 3.1 Run cloud backend tests for users / role permissions / tenant isolation
- [x] 3.2 Smoke-check Users UI: create member without org under active Verleiher → still visible (including “Ohne Organisation” filter)
- [x] 3.3 Note in PR: true orphans (null HC, no orgs) are not invented a Verleiher; org-linked users are backfilled
