## 1. Baseline and tests

- [x] 1.1 Confirm `defaults.VBtn.variant` is `outlined` in `cloud/frontend/src/main.ts` and leave it set
- [x] 1.2 Inventory free-form `v-btn` overrides (`variant="text"`, `variant="flat"`, inconsistent danger styles) under `cloud/frontend/src`
- [x] 1.3 Add or update frontend tests that assert outlined danger/primary recipes for representative components that already have specs (e.g. Login, one list delete, one config-card remove) before changing templates

## 2. Auth and shell

- [x] 2.1 Migrate `LoginPage.vue` primary CTA to outlined primary (remove flat if present)
- [x] 2.2 Migrate Header / Dashboard / onboarding / HelpLink action buttons to primary/secondary recipes

## 3. List/detail CRUD screens

- [x] 3.1 Migrate table `#item.actions` danger buttons to outlined + error + visible label (Users, Organisations, Articles, Appliances, and peers using outlined or text today)
- [x] 3.2 Migrate remaining list deletes that use `variant="text"` (Waiters, HireCompanies, PaymentTypes, Countries, TaxCodes, Ingredients, Organisation* sections, etc.) to outlined danger labels
- [x] 3.3 Align form footers (Back / Delete / Save) to secondary / danger / primary outlined recipes across CRUD screens

## 4. Event config and event detail

- [x] 4.1 Migrate config-card header removes from text icon buttons to outlined danger icon buttons (`mdi-delete`) across EventConfig* sections
- [x] 4.2 Migrate other event-config and event-tab actions (Add, Import, Refresh, dialogs) to primary/secondary outlined recipes
- [x] 4.3 Migrate EventStats / HostedPi / wizard buttons off `variant="flat"` / rogue text variants onto intents

## 5. Dialogs and remaining call sites

- [x] 5.1 Migrate dialog action rows (Cancel / Confirm / destructive) to secondary / primary / danger outlined recipes
- [x] 5.2 Sweep remaining `cloud/frontend` components for free-form `variant="text"` or `variant="flat"` on `v-btn`; leave only `v-btn-toggle` exemptions
- [x] 5.3 Grep-verify zero free-form non-outlined `v-btn` variants remain

## 6. Verification

- [x] 6.1 Run cloud frontend tests (`cd cloud/frontend && npm test` / project-standard script)
- [x] 6.2 Run lint for touched areas (`./scripts/lint.sh` or staged equivalent)
- [x] 6.3 Spot-check Login, one list with delete, one event-config card, one dialog in the UI
