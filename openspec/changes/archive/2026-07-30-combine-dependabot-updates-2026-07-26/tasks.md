## 1. Create combined branch

- [x] 1.1 Branch `cursor/combine-dependabot-updates-2026-07-26-c291` from updated `main` (cloud-agent branch; equivalent to planned `chore/…` name)
- [x] 1.2 Confirm open Dependabot set is still #214–#220 and no conflicting migration PR blocks them

## 2. Apply dependency bumps

- [x] 2.1 cloud/backend: bump `fastapi` to 0.140.0 and refresh `uv.lock` (#220)
- [x] 2.2 pi/backend: bump `fastapi` to 0.140.0 and refresh `uv.lock` (#219)
- [x] 2.3 cloud/hosted-pi-manager: bump `fastapi` to 0.140.0 in `uv.lock` (#216; `pyproject.toml` already `>=0.115.0`)
- [x] 2.4 cloud/frontend: install `vue-i18n@11.4.8`, `vuetify@4.1.6`, `@types/node@26.1.1` via `scripts/npm.sh` (#217)
- [x] 2.5 pi/frontend: install `@types/node@26.1.1` via `scripts/npm.sh` (#214)
- [x] 2.6 website: install `markdown-it@14.3.0`, `vite@8.1.5` via `scripts/npm.sh` (#215)
- [x] 2.7 root npm: install ESLint 10 stack (`eslint@10.8.0`, `@eslint/js@10.0.1`, `eslint-plugin-vue@10.10.0`, `globals@17.8.0`, `typescript-eslint@8.65.0`) via `scripts/npm.sh`; fix `preserve-caught-error` in `stripeConnect.ts` and `no-useless-assignment` in `paymentReceiptPrompt.ts` (#218)

## 3. Verify

- [x] 3.1 Run cloud backend tests (`cd cloud/backend && uv sync && uv run pytest`) — 456 passed
- [x] 3.2 Run pi backend tests (`cd pi/backend && uv sync && uv run pytest`) — 305 passed
- [x] 3.3 Run cloud frontend tests + typecheck (`npm test && npm run typecheck`) — 268 passed, typecheck clean
- [x] 3.4 Run pi frontend tests (`npm test`) — 366 passed
- [x] 3.5 Run website checks needed for #215 (install + build and/or lint as used in CI) — `npm test` + `npm run build` passed
- [x] 3.6 Run `./scripts/lint.sh` (critical for ESLint 10) — passed
- [x] 3.7 Confirm no `VERSION` change is included in the diff

## 4. Open PR and supersede Dependabot PRs

- [x] 4.1 Push branch and open PR titled to combine Dependabot updates, referencing #214–#220 — #222
- [x] 4.2 On each Dependabot PR (#214–#220), comment `Superseded by #222 — combining with …` and close without merge
- [x] 4.3 Merge combined PR after CI passes — #222 merged 2026-07-26
