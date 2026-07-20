## Context

Frontends (cloud Vue admin, pi PWA, and the marketing website build) currently run on **Node 20** in GitHub Actions and Docker (`node:20-alpine`). `@types/node` was recently pinned to the Node 20 line so TypeScript matches that runtime. Node 20 reached **EOL on 2026-03-24**. The Active LTS line is **Node 24** (codename Krypton); Node 26 is Current and not yet LTS.

The Pi frontend already has a known locale footgun: Swiss money formatting tests expect the ASCII apostrophe group separator (`1'234.56`). Newer ICU data (seen historically on Node 22+) can emit a different apostrophe glyph and fail CI unless tests or formatters account for it.

## Goals / Non-Goals

**Goals:**
- Run all frontend CI and Docker builds on Node 24 LTS.
- Keep TypeScript Node typings on the same major as the runtime.
- Keep Swiss money formatting correct and tests green on Node 24.
- Document the supported major so Dependabot/`@types/node` bumps cannot drift ahead of runtime again.

**Non-Goals:**
- Adopting Node 26 Current.
- Changing Python / uv / backend container bases.
- Reworking Dependabot batching policy (`dependency-maintenance`).
- Changing product UI locale formatting contracts for the cloud admin (Babel / vue-i18n) beyond what Node ICU forces for Pi unit tests.

## Decisions

### 1. Target Node 24 Active LTS (not 22 or 26)
- **Choice:** Pin CI and Docker to major `24`.
- **Why:** Longest supported Active LTS runway (EOL ~2028-04). Node 22 is Maintenance-only; Node 26 is Current until ~2026-10.
- **Alternatives:** Stay on 20 (EOL — rejected); jump to 26 (premature for production images — rejected).

### 2. Single coordinated PR for toolchain surfaces
- **Choice:** One feature branch updating workflows, Dockerfiles, `@types/node`, docs, and locale tests together.
- **Why:** Runtime and typings must move in lockstep; partial bumps recreate the #147 mismatch.
- **Alternatives:** Separate Dependabot PRs (rejected — already proven noisy and easy to mis-align).

### 3. Locale tests: normalize apostrophe, keep Swiss separators
- **Choice:** In Pi `formatAmount` tests (and any sibling hard-coded ICU asserts), normalize Unicode apostrophe variants before comparing, **or** assert via a helper that accepts both ASCII `'` (U+0027) and typographic `’` (U+2019) while still requiring apostrophe-style grouping and `.` decimals. Prefer not changing production format output unless product requires a specific code point.
- **Why:** Format correctness is “Swiss grouping + decimal point,” not a specific Unicode code point. Hard-coding `1'234.56` couples tests to ICU.
- **Alternatives:** Force ICU data / locale in Node flags (fragile across Docker/CI); change formatter to always emit ASCII apostrophe (possible follow-up if UI consistency demands it).

### 4. Website included
- **Choice:** Bump `website/Dockerfile.prod` with the frontends.
- **Why:** Same monorepo Node image family; leaving it on 20 reintroduces an EOL base.

### 5. Release labelling
- **Choice:** Open as a normal PR; apply `release:patch` when ready to ship (toolchain / security hygiene).
- **Why:** Matches `docs/RELEASE.md`; no manual `VERSION` edit.

## Risks / Trade-offs

- **[Risk] ICU / money test failures on Node 24** → Mitigate first with a failing-test-then-fix on the Pi money helpers under Node 24 locally and in CI.
- **[Risk] Native addon / Vite toolchain quirks on Alpine Node 24** → Mitigate by rebuilding frontend images and running `npm ci` + test + build in CI before merge.
- **[Risk] Developer machines still on Node 20 via nvm** → Update `AGENTS.md` to require Node 24; Cloud VM nvm default should follow.
- **[Trade-off] Skipping Node 22** → Slightly larger jump, but avoids two upgrades and lands on Active LTS.

## Migration Plan

1. Branch from `main`; write/adjust locale tests to green on Node 24 *before* relying on CI alone.
2. Update workflows → Dockerfiles → `@types/node` → docs.
3. Run cloud + pi frontend tests/builds and `./scripts/lint.sh`.
4. Merge via PR; label `release:patch` for one patch release.
5. **Rollback:** Revert the PR (restore Node 20 pins). Prefer forward-fix of locale tests over rolling back security EOL.

## Open Questions

- None blocking. Optional later: enforce `engines.node` in frontend `package.json` (`>=24 <25`) so npm warns on wrong local majors.
