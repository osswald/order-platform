## Why

After Vendiqo creates an organisation and invites the customer, org admins face a hire-company-shaped admin UI: a long “Erste Schritte” checklist that mixes optional finance with appliance lending they cannot create, plus scattered CRUD with no guided path to a sellable first event. Organisation setup and appliance lending are independent timelines — customers should configure catalogue and event without waiting on hardware.

## What Changes

- Add a soft, dismissible **first-event setup wizard** for organisation users (primary persona: `organisation_admin` after handover).
- Wizard steps: menu (categories + articles) → waiters → event (name + dates; create event early as `config`) → station + articles → app layout (suggest cells from station articles) → done with hosted Pi CTA and optional device-lending status (informational only).
- Soft dashboard CTA (“Set up your first event” / “Continue setup”) until the wizard is completed or dismissed for the organisation; does not block normal navigation or classic “New event”.
- Role-aware onboarding: remove or demote hire-company-only and optional finance/cash/stock/addon tasks from the customer first-sale path; never present lending as homework the customer must complete.
- Hardware remains hire-company owned; customers see lending status when present, never create appliances or lendings via the wizard.

## Capabilities

### New Capabilities
- `customer-first-event-wizard`: Soft first-event setup wizard and dashboard CTA for organisation users, including early event creation, station/layout completion, hosted Pi handoff, and role-aware first-sale readiness (vs hire-company hardware).

### Modified Capabilities
- _(none — existing onboarding checklist behavior will be narrowed for org users as part of this capability; no separate living spec today covers Erste Schritte requirements)_

## Impact

- **Cloud frontend**: new wizard UI/route or overlay; dashboard CTA; i18n (de/en); optional reshaping of `DashboardOnboardingCard` / `visibleOnboardingTasks` for org admins; reuse existing catalogue and event-config APIs where possible.
- **Cloud backend**: persistence for wizard completed/dismissed (and optional in-progress `event_id` / step) per organisation; possibly slim or role-filter `build_onboarding_tasks`; OpenAPI export + generated frontend types if new endpoints/schemas.
- **Out of scope**: self-serve Mietanfrage → org provisioning; hire-company handover checklist UI; changing lending/pairing APIs; Pi PWA flows beyond linking hosted Pi from the wizard done state.
