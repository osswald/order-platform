## 1. Branch and inventory

- [ ] 1.1 Confirm branch is cut from latest `main` (`cursor/combine-dependabot-updates-2026-07-30-2e77` or equivalent)
- [ ] 1.2 Confirm open Dependabot set is still #231–#236 and no conflicting migration PR blocks them

## 2. Apply dependency bumps

- [ ] 2.1 cloud/backend: bump `fastapi` to 0.141.1 and `stripe` to 15.4.0; refresh `uv.lock` (#236)
- [ ] 2.2 pi/backend: bump `fastapi` to 0.141.1; refresh `uv.lock` (#235)
- [ ] 2.3 cloud/hosted-pi-manager: bump lock to `fastapi` 0.141.1 and `uvicorn` 0.52.0; keep pyproject floors loose (`>=0.115.0` / `>=0.51.0`) (#234)
- [ ] 2.4 cloud/frontend: install `@types/node@26.1.2` via `scripts/npm.sh` (#232)
- [ ] 2.5 pi/frontend: install `@types/node@26.1.2` via `scripts/npm.sh` (#231)
- [ ] 2.6 root npm: install `@fission-ai/openspec@1.7.0` via `scripts/npm.sh` (#233)

## 3. Verify

- [ ] 3.1 Run cloud backend tests (`cd cloud/backend && uv sync && uv run pytest`)
- [ ] 3.2 Run pi backend tests (`cd pi/backend && uv sync && uv run pytest`)
- [ ] 3.3 Run cloud frontend tests + typecheck (`npm test && npm run typecheck`)
- [ ] 3.4 Run pi frontend tests (`npm test`)
- [ ] 3.5 Run `./scripts/lint.sh`
- [ ] 3.6 Confirm no `VERSION` change is included in the diff
- [ ] 3.7 Confirm FastAPI version matches across cloud backend, pi backend, and hosted-pi-manager locks

## 4. Open PR and supersede Dependabot PRs

- [ ] 4.1 Push branch and open PR titled to combine Dependabot updates, referencing #231–#236
- [ ] 4.2 On each Dependabot PR (#231–#236), comment `Superseded by #N — combining with …` and close without merge
- [ ] 4.3 Merge combined PR after CI passes
