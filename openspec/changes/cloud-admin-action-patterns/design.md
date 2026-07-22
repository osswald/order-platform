## Context

Cloud admin UI uses Vuetify 4 with a global default already set in `cloud/frontend/src/main.ts`:

```ts
defaults: {
  VBtn: { variant: 'outlined' },
  // …
}
```

Despite that, many components set `variant="text"` or `variant="flat"`, and delete actions split into three dialects (outlined label, text label, icon-only). This change makes outline-first the enforceable contract and migrates every free-form `v-btn` to a small set of intents. No shared wrapper components — recipes + Vuetify props only.

## Goals / Non-Goals

**Goals:**

- One visual language for actions: outlined surface; intent via `color`.
- Documented recipes for primary / secondary / danger and config-card icon remove.
- Full migration of cloud frontend buttons that currently override the default.
- Login and other CTAs remain outlined (no solid/flat exception).

**Non-Goals:**

- Custom `<AppButton>` / design-system package, Storybook, or token Figma library.
- Changing form field variants (already outlined via defaults).
- Pi frontend.
- Changing click behavior, confirms, or i18n keys (presentation only).
- Redesigning `v-btn-toggle` segmented controls.

## Decisions

### D1 — Intents, not fill variants

| Intent | Vuetify props | Typical labels |
|--------|---------------|----------------|
| primary | `color="primary"` (variant omitted → outlined) | Save, Add, Login, Apply |
| secondary | no color / default (outlined) | Back, Cancel, Refresh, Close |
| danger | `color="error"` (outlined) | Delete / Löschen |
| config-remove | `color="error"` + `icon="mdi-delete"` (outlined) | (icon only; aria via Vuetify icon button) |

**Rationale:** Hierarchy comes from color + placement, not filled vs outlined. Matches existing global default.

**Alternative considered:** Keep `flat` primary for Login / Hosted Pi start — rejected; product chose outlined everywhere including Login.

### D2 — No text/flat free-form buttons

After migration, free-form `v-btn` MUST NOT set `variant="text"` or `variant="flat"` (or any non-outlined variant). Rely on the global default or set `variant="outlined"` explicitly only when clarity helps.

**Exception:** `v-btn-toggle` children remain Vuetify toggle styling (not free-form action buttons).

**Alternative considered:** Allow text “quiet” deletes in tables — rejected; migrate those to outlined danger labels.

### D3 — Where labels vs icons

- **Lists / forms / dialogs:** danger actions use a **visible label** (`common.delete` / equivalent).
- **Event config card headers** (and similar dense card toolbars): danger remove uses **outlined icon-only** `mdi-delete` (still outlined, not text variant).

**Rationale:** Dense config UIs need compact chrome; lists need readable actions. Both stay outlined.

### D4 — Screen patterns

1. **Form footer:** secondary Back/Cancel + optional danger Delete + primary Save (rightmost primary).
2. **Table `#item.actions`:** outlined danger with label (size `small` when the table already uses compact actions).
3. **Config-card header:** title + outlined icon danger remove.
4. **Dialog actions:** secondary Cancel (outlined) + primary Confirm; destructive confirms use danger outlined if present.

### D5 — Implementation approach: migrate in place, no wrappers

Update templates to match recipes; strip redundant `variant="outlined"` only where noisy, or leave explicit outlined for readability — either is fine if the rendered variant is outlined.

**Alternative considered:** Introduce `<PrimaryBtn>` etc. — deferred; high churn for little gain on a Vuetify-only admin.

### D6 — Scope of migration

One change migrates **all** cloud frontend free-form buttons (not delete-only). Inventory via search for `variant="text"`, `variant="flat"`, and inconsistent danger styles; align remaining primary/secondary that omit color incorrectly.

## Risks / Trade-offs

- **[Risk] Large visual PR** → Mitigation: single focused PR; no behavior changes; screenshot key screens (Login, one list, one event-config section) in PR description.
- **[Risk] Icon-only outlined buttons wider than text icons** → Mitigation: accepted; density trade for consistency; keep `density` / `size` as today where set.
- **[Risk] Tests asserting `variant="text"` / flat markup** → Mitigation: grep frontend tests and update assertions first (TDD where tests exist).
- **[Risk] Accidental reintroduction** → Mitigation: short Cursor/docs note in this change’s archive path; optional follow-up ESLint rule later (out of scope unless trivial).

## Migration Plan

1. Branch from `main`.
2. Update/add frontend tests that lock recipes where components are already tested.
3. Migrate by area: auth/Login → list/detail CRUD → event config → dialogs/misc (Hosted Pi, Stripe, wizards).
4. Grep for remaining `variant="text"` / `variant="flat"` on `v-btn`; zero free-form hits before merge.
5. Run cloud frontend tests + lint.
6. Rollback = revert PR (CSS/presentation only).

## Open Questions

- None blocking. Optional follow-up: ESLint restriction on `VBtn` variant overrides (separate change).
