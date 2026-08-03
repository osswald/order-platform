## 1. Baseline and dependencies

- [x] 1.1 Record current `npm run build` chunk sizes (JS/CSS/font) as a before baseline in the PR description
- [x] 1.2 Add `@mdi/js` (or chosen SVG icon dependency) and plan removal of `@mdi/font` CSS import
- [x] 1.3 Write failing Vitest coverage for icon map completeness (every `mdi-*` used in `src/` must resolve) and for waiters org-scoped fetch query param

## 2. Route and vendor code splitting

- [x] 2.1 Convert `router/index.ts` feature routes to dynamic `() => import(...)` (keep login/shell eager only if needed)
- [x] 2.2 Ensure Event Stats, Help Center, and Orderjutsu import land in separate async chunks (charts/markdown not in the initial shell)
- [x] 2.3 Defer Help markdown loading (non-eager glob / dynamic import) so markdown-it is not in the initial chunk
- [x] 2.4 Smoke-test navigation to dashboard, events, stats, help, and import after lazy loading

## 3. Vuetify and icons payload

- [x] 3.1 Remove `import * as components/directives` registration from `main.ts`; rely on `vite-plugin-vuetify` auto-import
- [x] 3.2 Verify date picker / data table / dialog / navigation drawers still render (fix gaps by ensuring SFC usage is scanned)
- [x] 3.3 Switch icon delivery to `@mdi/js` (or SVG) subset; remove full MDI webfont CSS import
- [x] 3.4 Update components that rely on string `mdi-*` icon props to the new icon scheme where required

## 4. Request parallelism

- [x] 4.1 Parallelize independent auth bootstrap fetches in `useAuthSession` once session prerequisites are met
- [x] 4.2 Parallelize Articles mount fetches (categories, articles, ingredients) with `Promise.all` where independent
- [x] 4.3 Parallelize Event Stats mount fetches using route `event_id` where possible; only sequence true dependencies
- [x] 4.4 Add/adjust Vitest or composable tests proving concurrent start (or at least no artificial serial awaits) for the changed paths

## 5. Org-scoped list fetching

- [x] 5.1 Audit list APIs used by Events, Articles, Waiters, Appliances for existing organisation (or equivalent) filters
- [x] 5.2 Wire Waiters (and any other lists with an existing filter) to request the active organisation scope instead of tenant-wide + client filter
- [x] 5.3 Leave unsupported lists on client filter; document follow-ups — do not add breaking pagination APIs in this change

## 6. Verification

- [x] 6.1 Run cloud frontend tests (`npm test`) and typecheck
- [x] 6.2 Re-run production build; compare chunk sizes to baseline; confirm initial shell excludes stats charts and help markdown
- [x] 6.3 Run `./scripts/lint.sh --staged` (or full lint for touched areas) before commit
