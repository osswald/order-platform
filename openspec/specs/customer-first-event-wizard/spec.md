# customer-first-event-wizard Specification

## Purpose

Guides organisation users through a soft, dismissible first-event setup so they can build a sellable catalogue and event without depending on appliance lending or hire-company admin flows.

## Requirements

### Requirement: Soft first-event setup CTA on the dashboard
The cloud admin SHALL show a dismissible first-event setup call-to-action on the organisation dashboard when the organisation has not completed or dismissed first-event setup. The CTA MUST NOT block navigation to other areas or prevent creating events through the existing event UI.

#### Scenario: Eligible organisation sees the CTA
- **WHEN** an organisation user with an active organisation views the dashboard and first-event setup is neither completed nor dismissed for that organisation
- **THEN** the dashboard shows a call-to-action to start or continue first-event setup

#### Scenario: User dismisses the CTA
- **WHEN** the user dismisses first-event setup for the organisation
- **THEN** the dashboard no longer shows the first-event setup CTA for that organisation

#### Scenario: CTA does not hijack navigation
- **WHEN** first-event setup is available
- **THEN** the user can still open Events, catalogue pages, and create a new event through the classic flow without entering the wizard

### Requirement: Guided first-event wizard steps
The system SHALL provide a guided first-event wizard with the ordered steps: menu (at least one category and one sellable article), waiters (at least one waiter), event master data (name and date range), station with assigned articles, and app layout. Completing the wizard MUST leave the organisation with a `config`-status event that has at least one station with articles, at least one event waiter, and at least one app layout suitable for POS use.

#### Scenario: Full happy path
- **WHEN** the user completes all wizard steps for an organisation with an empty or incomplete catalogue
- **THEN** the organisation has catalogue articles and waiters, and a `config` event with station articles, event waiters, and an app layout

#### Scenario: Skip completed catalogue steps
- **WHEN** the organisation already has at least one sellable article and at least one waiter before the wizard starts
- **THEN** the wizard allows the user to skip or short-circuit the menu and waiters steps and continue with event setup

### Requirement: Event is created early in the wizard
The wizard SHALL create the event when the user submits event name and date range (before station and layout steps), using status `config` and product-safe payment defaults. Later wizard steps MUST configure that same event.

#### Scenario: Event exists before station and layout
- **WHEN** the user finishes the event master-data step
- **THEN** an event record exists in `config` status and subsequent station and layout steps target that event

#### Scenario: Resume after early create
- **WHEN** the user leaves the wizard after the event was created but before setup is marked complete
- **THEN** returning via the dashboard CTA continues setup for that in-progress event rather than forcing a brand-new event

### Requirement: Hosted Pi and hardware status at completion
After the minimum first-event configuration is complete, the wizard SHALL offer testing via hosted Pi (when available for `config` events) and MAY show appliance-lending status as informational only. The wizard MUST NOT require appliance lending, pairing, or hire-company actions to finish customer first-event setup.

#### Scenario: Done without lending
- **WHEN** the user finishes station and layout steps and the organisation has no appliance lending
- **THEN** first-event setup can still be marked complete and the user is offered hosted Pi testing without being blocked on devices

#### Scenario: Lending shown as status only
- **WHEN** the organisation has a current or planned appliance lending
- **THEN** the wizard done state may show those dates or status as information without presenting lending as a customer task to create

### Requirement: Role-aware first-sale onboarding for organisation users
For organisation admins and members, the first-sale onboarding experience MUST NOT present hire-company-only actions (create appliance lending, pair appliances) as tasks the customer must complete. Optional finance, cash-register, stock, and addon-linking tasks MUST NOT be required to complete first-event setup.

#### Scenario: Org admin is not tasked with creating lendings
- **WHEN** an organisation admin views first-sale onboarding or the wizard
- **THEN** they are not required to create an appliance lending to complete first-event setup

#### Scenario: Optional capabilities stay optional
- **WHEN** an organisation completes first-event setup without VAT bookkeeping, cash registers, stock monitoring, or article addons
- **THEN** first-event setup is still considered complete

### Requirement: Wizard state is organisation-scoped
Completion and dismissal of first-event setup SHALL be stored per organisation so that after one successful first-event setup (or dismiss), the soft CTA does not reappear for that organisation’s users. A second event MUST use the classic event create or copy flows rather than re-triggering the first-event CTA by default.

#### Scenario: After completion CTA stays hidden
- **WHEN** first-event setup is marked complete for an organisation
- **THEN** organisation users no longer see the first-event setup CTA on the dashboard for that organisation

#### Scenario: Second event uses classic flow
- **WHEN** an organisation that already completed first-event setup creates another event
- **THEN** creation uses the existing event UI (or copy) and does not reopen the first-event wizard by default
