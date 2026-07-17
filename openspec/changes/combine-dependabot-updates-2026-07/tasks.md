# Tasks: Combine open Dependabot dependency updates (July 2026)

## 1. Land PR #120 first

- [x] 1.1 Confirm PR #120 CI is green after the merge of `origin/main` (commit b844111) and merge it into `main`
- [x] 1.2 Verify Dependabot auto-closed #125 (`@vitest/coverage-v8` 4.1.10 already on `main`); close it manually otherwise

## 2. Create the combined branch

- [x] 2.1 Branch `chore/combine-dependabot-updates-2026-07` from updated `main`
- [x] 2.2 GitHub Actions: bump `actions/setup-node` 6 → 7 in all workflows under `.github/workflows/` (#121)
- [x] 2.3 cloud/backend: widen `httpx2` to `>=2.7.0` in requirements (#123)
- [x] 2.4 pi/backend: widen `httpx2` to `>=2.7.0` in requirements (#122)
- [x] 2.5 cloud/frontend: `npm install vue@3.5.40 vue-router@5.2.0` and `npm install -D @vitejs/plugin-vue@6.0.8 @typescript-eslint/parser@8.64.0` via `scripts/npm.sh` (#131, #129, #126, #133)
- [x] 2.6 pi/frontend: `npm install vue@3.5.40` and `npm install -D vite@8.1.5 @vitejs/plugin-vue@6.0.8 @types/node@26.1.1 @typescript-eslint/parser@8.64.0` via `scripts/npm.sh` (#132, #124, #130, #128, #127)

## 3. Verify

- [x] 3.1 Run cloud backend tests (`cd cloud/backend && pytest`) — 372 passed
- [x] 3.2 Run pi backend tests (`cd pi/backend && pytest`) — 267 passed
- [x] 3.3 Run cloud frontend tests + typecheck (`npm test && npm run typecheck`), including the Vuetify 4 migration contract spec — 238 passed, typecheck clean
- [x] 3.4 Run pi frontend tests (`npm test`) — 219 passed
- [x] 3.5 Run `./scripts/lint.sh` — passed
- [x] 3.6 Confirm no `VERSION` change is included in the diff

## 4. Open PR and close superseded Dependabot PRs

- [x] 4.1 Push branch and open PR titled "Combine 12 open Dependabot dependency updates" referencing #121–#124, #126–#133
- [ ] 4.2 Merge after CI passes
- [ ] 4.3 Close any Dependabot PRs GitHub does not auto-close, commenting with the combined PR link
