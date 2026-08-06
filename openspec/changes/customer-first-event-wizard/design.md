## Context

See proposal.md for motivation. Today the cloud admin already has:
- Organisation-scoped catalogue (categories, articles, waiters) and event config (stations, event waiters, layouts) with autosave APIs
- Event create defaults (`config`, `pay_later`, `["cash"]`, feature flags off)
- Hosted Pi for `config` events (`/events/{id}/hosted-pi`) without requiring lending
- Dashboard onboarding checklist (`onboarding_tasks.py` + `DashboardOnboardingCard`) that is role-agnostic and includes lending, VAT, accounting, cash registers, stock, and addons
- Permission split: org admins manage catalogue/events/org settings; only tenant admins create appliances and lendings

Organisation creation and appliance lending are independent; the customer path must not wait on hardware.

## Goals / Non-Goals

**Goals:**
- Soft, dismissible first-event wizard with early event create at the name/dates step
- Persist completed/dismissed (and in-progress event) per organisation
- Reuse existing catalogue and event-config APIs; thin UX layer, not a parallel write path
- Role-aware narrowing of first-sale onboarding so org users are not assigned hire-company homework
- Hosted Pi as the confidence moment; lending as read-only status

**Non-Goals:**
- Self-serve signup from Mietanfrage
- Hire-company “ready to hand over” checklist UI (may come later)
- Changing edge lending hard-gates for physical Pi
- Replacing classic event create/copy for subsequent events
- Building a full Orderjutsu-style import; this is a thinner guided create

## Decisions

### 1. Soft CTA (option B), not a forced first-login wizard
**Choice:** Dashboard card/CTA until completed or dismissed; classic nav always available.  
**Why:** Matches “customer after handover” without trapping experienced users or tenant admins acting in an org.  
**Alternatives:** Forced wizard on first login (too aggressive); wizard only when clicking New event once (weaker discovery).

### 2. Organisation-scoped completion flag
**Choice:** Store `first_event_setup_completed_at` / `first_event_setup_dismissed_at` (and optional `in_progress_event_id`) on the organisation or a small org-level state table — not per user.  
**Why:** Venues share one setup; per-user flags would re-prompt colleagues. Aligns with “second event = classic flow.”  
**Alternatives:** Per-user dismiss (flexible but noisy); reuse only `UserOrganisationOnboardingDismissal` (already per-user and tied to the old checklist).

### 3. Create event at step 3 via existing `POST /events`
**Choice:** Wizard collects name + start/end, creates with `status=config` and default payment flags; steps 4–5 call existing station/waiter/layout endpoints for that `event_id`.  
**Why:** Matches current admin model; enables hosted Pi and resume without a draft-event table.  
**Alternatives:** Draft entity until the end (extra model); create placeholder event at wizard start with fake dates (worse UX).

### 4. Wizard UI as dedicated flow, not rewriting Events.vue tabs
**Choice:** New wizard view/route (or modal stepper) that composes focused forms and navigates to hosted Pi / event detail on done.  
**Why:** Event detail UI is feature-dense; a separate path keeps first-run thin. Deep-link to event detail remains the escape hatch.  
**Alternatives:** Drive the existing multi-tab Events UI with coach marks (high coupling, still noisy).

### 5. Catalogue steps write through normal org APIs
**Choice:** Category → article → waiter creation uses existing endpoints; skip when counts already satisfy minimums.  
**Why:** No duplicate persistence; Orderjutsu remains the bulk-import path.  
**Minimum for “menu done”:** ≥1 non-addition article (and thus ≥1 category). **Waiters done:** ≥1 org waiter; event-waiter assignment happens after event create (step 3+) as part of event config.

### 6. Layout auto-suggest
**Choice:** After station articles are set, offer a one-click layout that creates cells from those articles (labels from article names; default/org palette colors where available). User can edit before finish.  
**Why:** Station→layout subset rule is the main silent footgun; suggestion teaches the model.  
**Alternatives:** Empty layout only (keeps today’s friction); force a fixed template grid.

### 7. Relationship to Erste Schritte checklist
**Choice:** For organisation admins/members, filter or replace the first-sale checklist so it does not require `appliance_lending`, and does not treat VAT/accounting/cash registers/stock/addons as required for “first event done.” Prefer the wizard CTA as the primary path; keep a shortened optional checklist or help links for advanced setup.  
**Why:** Spec requires role-aware first-sale onboarding; today’s `build_onboarding_tasks` is role-agnostic.  
**Alternatives:** Leave checklist unchanged alongside wizard (conflicting guidance); delete checklist entirely (loses value for tenant admins).

### 8. Hardware status chip
**Choice:** Read existing org lending summary (dashboard already exposes lending buckets); show informational copy only. Never call create-lending from the wizard. Fix any org-admin UI that shows “Lend appliances” without tenant-admin gate as a small related fix.  
**Why:** Lending is not linked to org create; customers must not hit 403 homework.

### 9. API surface
**Choice:** Prefer a small org-level read/update for wizard state (e.g. get/patch first-event setup progress on the organisation or dashboard summary) rather than encoding everything in the old per-user onboarding task table. Wizard content steps keep using existing CRUD.  
**Why:** Clear product semantics (org completed setup); OpenAPI types regenerated once.  
**Alternatives:** Only frontend localStorage (breaks multi-device / multi-user); overload onboarding task dismiss IDs (opaque and per-user).

## Risks / Trade-offs

- **[Abandoned config events]** → User creates event at step 3 then leaves → Mitigation: CTA becomes “Continue setup”; orphan `config` events remain visible in Events list; no auto-delete in v1.
- **[Checklist vs wizard dual messaging]** → Mitigation: role-filter checklist in the same change; copy points advanced topics to Help.
- **[Layout suggest quality]** → One cell per article may be crude for large menus → Mitigation: allow edit in step 5; cap or warn if article count is high.
- **[Tenant admin using customer CTA]** → Acceptable; same org-scoped flag.
- **[Physical Pi still dark without lending]** → Expected; hosted Pi covers testing; status chip sets expectation without blocking completion.

## Migration Plan

- Additive schema/API for org wizard state; default “not completed / not dismissed” for existing orgs so CTA can appear where useful (product may later hide CTA if org already has a non-config or fully configured event — optional heuristic in implementation).
- No data backfill required for v1; optional: auto-mark complete if org already has an event with station + layout + event waiter to avoid nagging mature customers.
- Rollback: feature-flag or hide CTA/route; leftover org columns/state are harmless.

## Open Questions

- Exact auto-complete heuristic for mature orgs (hide CTA if any event already has layout + station articles) — implementer can choose a conservative default without changing specs.
- Whether member role (non-admin) sees the same CTA as org admin — default yes if they can create events/catalogue; otherwise limit to `organisation_admin` / organisation managers.
