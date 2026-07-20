## 1. Locale test readiness (before runtime bump)

- [x] 1.1 Add or adjust Pi frontend tests so Swiss `formatAmount` grouping accepts ASCII and typographic apostrophes while still requiring `.` decimals
- [x] 1.2 Confirm related Pi money/format assertions do not hard-code only `U+0027`

## 2. Runtime and image pins

- [x] 2.1 Update GitHub Actions Node installs to `24` in `frontend-tests.yml`, `lint.yml`, and `openapi-sync.yml`
- [x] 2.2 Update frontend/website Docker bases from `node:20-alpine` to `node:24-alpine` (`cloud/frontend`, `pi/frontend`, `website`)
- [x] 2.3 Update `AGENTS.md` (and any Cloud VM nvm notes) to require Node 24 instead of Node 20

## 3. TypeScript declarations

- [x] 3.1 Install `@types/node@24` in `cloud/frontend` and `pi/frontend` via `scripts/npm.sh` and commit lockfile changes
- [x] 3.2 Optionally add `engines.node` (`>=24 <25`) to both frontend `package.json` files if desired for local mismatch warnings

## 4. Verification

- [x] 4.1 Run Pi frontend tests and production build on Node 24
- [x] 4.2 Run cloud frontend tests, typecheck, and production build on Node 24
- [x] 4.3 Run `./scripts/lint.sh`
- [ ] 4.4 Archive openspec
- [ ] 4.5 Open PR from `main`, apply `release:patch` when ready to ship, merge after CI green
