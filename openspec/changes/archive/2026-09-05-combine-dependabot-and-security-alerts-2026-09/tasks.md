## 1. Branch and inventory

- [x] 1.1 Cut a feature branch from latest `main` (no `VERSION` change)
- [x] 1.2 Confirm open Dependabot set is still #313, #315, #317–#322 and that `js-yaml@4.3.1` and `nanoid@3.3.18` are published on npm

## 2. Same-origin navigation (tests first)

- [x] 2.1 Add unit tests for a same-origin path helper covering `/events`, query/hash preservation, `//evil.example`, `https://evil.example`, `javascript:` URLs, backslashes, and non-strings (fallback `/dashboard`)
- [x] 2.2 Implement `cloud/frontend/src/utils/safeInternalPath.ts` so tests pass
- [x] 2.3 Add LoginPage tests that a protocol-relative `redirect` query does not assign `window.location` and falls back to `/dashboard`, and that `/events` is accepted
- [x] 2.4 Wire the helper into `LoginPage.vue` and `useAuthSession.ts` (keep hard reload; only constrain the URL)
- [x] 2.5 Run `cd cloud/frontend && npm test` for the new helper and login/session cases

## 3. Apply grouped Dependabot bumps

- [x] 3.1 Root npm: install OpenSpec 1.10.0 and the grouped ESLint/globals/typescript-eslint updates from #313 via `scripts/npm.sh`
- [x] 3.2 `cloud/frontend`: apply grouped package.json bumps from #322 via `scripts/npm.sh`
- [x] 3.3 `pi/frontend`: apply grouped package.json bumps from #321 via `scripts/npm.sh`
- [x] 3.4 `website`: markdown-it 15.0.1 and Vite 8.2.2 via `scripts/npm.sh`
- [x] 3.5 `cloud/backend`: refresh `uv.lock` to pypdf 6.16.2 and the other #318 lock bumps; set `pypdf>=6.16.1,<7` in `pyproject.toml`
- [x] 3.6 `pi/backend`: SQLAlchemy 2.0.52 and httpx2 2.12.0 in `uv.lock`
- [x] 3.7 `cloud/hosted-pi-manager`: pydantic 2.13.5 in `uv.lock`
- [x] 3.8 Bump `actions/setup-java` from v5 to v6 in `.github/workflows/android-release.yml` unless apply-time docs show a breaking input change for this usage

## 4. Security floors grouped PRs missed

- [x] 4.1 Raise `js-yaml` overrides to `^4.3.1` in root, cloud frontend, and pi frontend; refresh those lockfiles so installed versions are ≥ 4.3.1
- [x] 4.2 Add `nanoid` overrides `^3.3.18` in cloud frontend, pi frontend, and website; refresh lockfiles so installed versions are ≥ 3.3.18
- [x] 4.3 Raise `postcss` overrides to `^8.5.23` in cloud frontend and website; refresh lockfiles so installed versions are ≥ 8.5.23
- [x] 4.4 Raise `pi/frontend/tests/package-audit.test.ts` js-yaml floor to 4.3.1 and add equivalent js-yaml/nanoid/postcss floor tests for cloud frontend

## 5. Verify

- [x] 5.1 Run cloud backend tests (`cd cloud/backend && uv sync && uv run pytest`)
- [x] 5.2 Run pi backend tests (`cd pi/backend && uv sync && uv run pytest`)
- [x] 5.3 Run cloud frontend tests + typecheck (`npm test && npm run typecheck`)
- [x] 5.4 Run pi frontend tests (`npm test`)
- [x] 5.5 Run website tests if `website/package-lock.json` changed
- [x] 5.6 Run `./scripts/lint.sh`
- [x] 5.7 Confirm the diff contains no `VERSION` change

## 6. Open PR and supersede Dependabot PRs

- [x] 6.1 Push the branch and open one PR that combines Dependabot updates, the extra security floors, and CodeQL #21/#22, referencing #313, #315, #317–#322
- [x] 6.2 On each Dependabot PR, comment `Superseded by #N — combining with …` and close without merge
