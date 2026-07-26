## 1. Create combined branch

- [ ] 1.1 Branch `chore/combine-dependabot-updates-2026-07-26` from updated `main`
- [ ] 1.2 Confirm open Dependabot set is still #214–#220 and no conflicting migration PR blocks them

## 2. Apply dependency bumps

- [ ] 2.1 cloud/backend: bump `fastapi` to 0.140.0 and refresh `uv.lock` (#220)
- [ ] 2.2 pi/backend: bump `fastapi` to 0.140.0 and refresh `uv.lock` (#219)
- [ ] 2.3 cloud/hosted-pi-manager: bump `fastapi` to 0.140.0 in `pyproject.toml` + `uv.lock` (#216)
- [ ] 2.4 cloud/frontend: install `vue-i18n@11.4.8`, `vuetify@4.1.6`, `@types/node@26.1.1` via `scripts/npm.sh` (#217)
- [ ] 2.5 pi/frontend: install `@types/node@26.1.1` via `scripts/npm.sh` (#214)
- [ ] 2.6 website: install `markdown-it@14.3.0`, `vite@8.1.5` via `scripts/npm.sh` (#215)
- [ ] 2.7 root npm: install ESLint 10 stack (`eslint@10.8.0`, `@eslint/js@10.0.1`, `eslint-plugin-vue@10.10.0`, `globals@17.8.0`, `typescript-eslint@8.65.0`) via `scripts/npm.sh`; fix config/peers if lint breaks (#218)

## 3. Verify

- [ ] 3.1 Run cloud backend tests (`cd cloud/backend && uv sync && uv run pytest`)
- [ ] 3.2 Run pi backend tests (`cd pi/backend && uv sync && uv run pytest`)
- [ ] 3.3 Run cloud frontend tests + typecheck (`npm test && npm run typecheck`)
- [ ] 3.4 Run pi frontend tests (`npm test`)
- [ ] 3.5 Run website checks needed for #215 (install + build and/or lint as used in CI)
- [ ] 3.6 Run `./scripts/lint.sh` (critical for ESLint 10)
- [ ] 3.7 Confirm no `VERSION` change is included in the diff

## 4. Open PR and supersede Dependabot PRs

- [ ] 4.1 Push branch and open PR titled to combine Dependabot updates, referencing #214–#220
- [ ] 4.2 On each Dependabot PR (#214–#220), comment `Superseded by #N — combining with …` and close without merge (if not auto-closed after the combined merge)
- [ ] 4.3 Merge combined PR after CI passes
