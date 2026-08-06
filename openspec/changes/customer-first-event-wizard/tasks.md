## 1. Backend wizard state API

- [ ] 1.1 Write failing tests for organisation first-event setup state (read defaults; complete; dismiss; set/clear in-progress event id; org-scoped visibility)
- [ ] 1.2 Add organisation-scoped persistence for completed/dismissed timestamps and optional in-progress event id (schema patch + model)
- [ ] 1.3 Expose read/update on dashboard summary and/or organisation endpoints; enforce organisation manager access
- [ ] 1.4 Optionally auto-mark setup complete for orgs that already have a minimally configured event (station with articles + event waiter + layout) so mature orgs are not nagged
- [ ] 1.5 Export OpenAPI and regenerate cloud frontend API types

## 2. Role-aware first-sale onboarding

- [ ] 2.1 Write failing tests that org-facing first-sale onboarding does not require appliance lending, VAT/accounting, cash registers, stock, or addon linking to be “first event ready”
- [ ] 2.2 Filter or reshape `build_onboarding_tasks` / frontend visibility for organisation admins and members so hire-company-only lending is not customer homework
- [ ] 2.3 Gate any org UI “Lend appliances” actions that call tenant-admin-only APIs behind tenant-admin access (match API + help)

## 3. Wizard UI shell and dashboard CTA

- [ ] 3.1 Add dashboard soft CTA (start / continue / dismiss) driven by org wizard state; keep classic navigation and New event available
- [ ] 3.2 Add wizard route/view with step indicator for menu → waiters → event → station → layout → done
- [ ] 3.3 Add de/en i18n strings for CTA, steps, skip, dismiss, resume, and done states
- [ ] 3.4 Wire resume: if in-progress event exists, open wizard at the first incomplete step for that event

## 4. Wizard steps (reuse existing APIs)

- [ ] 4.1 Menu step: create category + articles (or skip when ≥1 sellable article exists)
- [ ] 4.2 Waiters step: create waiter with PIN (or skip when ≥1 org waiter exists)
- [ ] 4.3 Event step: create `config` event via existing create API with name/dates and safe payment defaults; store as in-progress event id
- [ ] 4.4 Station step: create one station and assign selected articles on the in-progress event
- [ ] 4.5 Assign at least one event waiter on the in-progress event (from org waiters)
- [ ] 4.6 Layout step: offer auto-suggested cells from station articles; allow edit; persist via existing layout APIs
- [ ] 4.7 Done step: mark setup complete; offer hosted Pi entry for the event; show optional lending status as informational only (never block)

## 5. Verification

- [ ] 5.1 Add frontend unit/component tests for CTA visibility, dismiss, resume, and skip logic
- [ ] 5.2 Run cloud backend and cloud frontend tests for touched areas
- [ ] 5.3 Run `./scripts/lint.sh` (or staged) before commit
