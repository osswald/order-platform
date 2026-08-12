## Purpose

Ensures platform admins who are operating in an active Verleiher context can reach the same Verleiher settings entry as tenant admins, without granting that nav to users who have no active hire company.

## ADDED Requirements

### Requirement: Platform admins with active Verleiher see Verleiher settings

The cloud admin navigation SHALL show the Verleiher-Einstellungen / hire-company settings item when the user is a `tenant_admin`, or a `platform_admin` with an active hire company selected. Organisation-only users MUST NOT see that item. Route access for settings MUST remain consistent with that nav gate.

#### Scenario: Platform admin with active Verleiher sees settings

- **WHEN** a platform admin has selected an active hire company
- **THEN** the Verwaltung (or equivalent) nav includes Verleiher settings

#### Scenario: Platform admin without Verleiher does not see settings

- **WHEN** a platform admin has no active hire company selected
- **THEN** the Verleiher settings nav item is not shown
