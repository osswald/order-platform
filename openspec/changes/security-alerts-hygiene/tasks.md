## 1. Dependabot coverage

- [x] 1.1 Add grouped `package-ecosystem: npm` entries for `/` and `/website` to `.github/dependabot.yml` (same schedule, PR limit, and `groups:` pattern as existing npm directories)
- [x] 1.2 Optionally add `ignore:` for `typescript` major updates under cloud/pi frontend entries if TS 7 is still proposed in grouped PRs (document why)

## 2. Lockfile remediations (open High alerts)

- [x] 2.1 In repo root, bump/resolve `brace-expansion` to patched versions (`≥1.1.16` and `≥5.0.7` as applicable) and `js-yaml` to `≥4.3.0`; refresh `package-lock.json` (use `overrides` only if parents cannot reach patches)
- [x] 2.2 In `cloud/frontend`, bump/resolve `js-yaml` to `≥4.3.0` and refresh `package-lock.json`
- [x] 2.3 In `website/`, bump/resolve `linkify-it` to `≥5.0.2` and `postcss` to `≥8.5.18`; refresh `package-lock.json`
- [x] 2.4 Verify patched versions are present via `npm ls` (or lockfile inspection) for each remediated package

## 3. GitHub Actions permissions

- [x] 3.1 Add an explicit least-privilege `permissions` block to the `guards` job in `.github/workflows/pi-docker.yml` (CodeQL alert #19)
- [x] 3.2 Audit all `.github/workflows/*.yml` jobs for missing `permissions`; fix any stragglers in the same change

## 4. Process docs (triage + Dependabot lifecycle)

- [x] 4.1 Document security-alert triage (fix patched versions first; dismiss only with written rationale) and Dependabot PR lifecycle (combine/supersede comment, ignore for peer-incompatible majors, verify “no longer updatable”) in `docs/dependency-updates.md` or a short AGENTS.md section
- [x] 4.2 Link that doc from AGENTS.md if it lives under `docs/`

## 5. Verification

- [x] 5.1 Run `./scripts/lint.sh` (or staged equivalent) after lockfile and workflow edits
- [x] 5.2 Run `npm ci && npm run build` in `website/` after website lockfile changes
- [x] 5.3 Run cloud frontend checks touched by the js-yaml bump (`npm test` and/or `npm run typecheck` as appropriate)
- [ ] 5.4 After merge to `main`, confirm Dependabot alerts #52–#57 and Code scanning alert #19 close or clear on the Security tab (allow dependency-graph refresh)
