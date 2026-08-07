## 1. Backend wizard state API

- [x] 1.1 Write failing tests for organisation first-event setup state (read defaults; complete; dismiss; set/clear in-progress event id; org-scoped visibility)
- [x] 1.2 Add organisation-scoped persistence for completed/dismissed timestamps and optional in-progress event id (schema patch + model)
- [x] 1.3 Expose read/update on dashboard summary and/or organisation endpoints; enforce organisation manager access
- [x] 1.4 Optionally auto-mark setup complete for orgs that already have a minimally configured event (station with articles + event waiter + layout) so mature orgs are not nagged
- [x] 1.5 Export OpenAPI and regenerate cloud frontend API types

## 2. Role-aware first-sale onboarding

- [x] 2.1 Write failing tests that org-facing first-sale onboarding does not require appliance lending, VAT/accounting, cash registers, stock, or addon linking to be “first event ready”
- [x] 2.2 Filter or reshape `build_onboarding_tasks` / frontend visibility for organisation admins and members so hire-company-only lending is not customer homework
- [x] 2.3 Gate any org UI “Lend appliances” actions that call tenant-admin-only APIs behind tenant-admin access (match API + help)

## 3. Wizard UI shell and dashboard CTA

- [x] 3.1 Add dashboard soft CTA (start / continue / dismiss) driven by org wizard state; keep classic navigation and New event available
- [x] 3.2 Add wizard route/view with step indicator for menu → waiters → event → station → layout → done
- [x] 3.3 Add de/en i18n strings for CTA, steps, skip, dismiss, resume, and done states
- [x] 3.4 Wire resume: if in-progress event exists, open wizard at the first incomplete step for that event

## 4. Wizard steps (reuse existing APIs)

- [x] 4.1 Menu step: create category + articles (or skip when ≥1 sellable article exists)
- [x] 4.2 Waiters step: create waiter with PIN (or skip when ≥1 org waiter exists)
- [x] 4.3 Event step: create `config` event via existing create API with name/dates and safe payment defaults; store as in-progress event id
- [x] 4.4 Station step: create one station and assign selected articles on the in-progress event
- [x] 4.5 Assign at least one event waiter on the in-progress event (from org waiters)
- [x] 4.6 Layout step: offer auto-suggested cells from station articles; allow edit; persist via existing layout APIs
- [x] 4.7 Done step: mark setup complete; offer hosted Pi entry for the event; show optional lending status as informational only (never block)

## 5. Verification

- [x] 5.1 Add frontend unit/component tests for CTA visibility, dismiss, resume, and skip logic
- [x] 5.2 Run cloud backend and cloud frontend tests for touched areas
- [x] 5.3 Run `./scripts/lint.sh` (or staged) before commit
