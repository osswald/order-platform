## ADDED Requirements

### Requirement: Home Verleiher for members and organisation-admins

The system SHALL persist `hire_company_id` as the user’s home Verleiher for roles `member` and `organisation_admin`. Platform admins SHALL continue to have `hire_company_id` unset. Tenant admins SHALL continue to require `hire_company_id` for their Verleiher. Presence of `hire_company_id` alone MUST NOT grant Verleiher-admin permissions.

#### Scenario: Create member without organisations under active Verleiher

- **WHEN** a platform-admin or Verleiher-admin creates a user with role `member`, empty `organisation_ids`, under active Verleiher V
- **THEN** the user is stored with `hire_company_id` equal to V
- **AND** a subsequent `GET /users/` for Verleiher V includes that user

#### Scenario: Create organisation-admin without organisations under active Verleiher

- **WHEN** a platform-admin or Verleiher-admin creates a user with role `organisation_admin`, empty `organisation_ids`, under active Verleiher V
- **THEN** the user is stored with `hire_company_id` equal to V
- **AND** a subsequent `GET /users/` for Verleiher V includes that user

#### Scenario: Organisation-admin actor still requires organisations on create

- **WHEN** an organisation-admin creates a user with empty `organisation_ids`
- **THEN** the system rejects the request with an organisation-required error

#### Scenario: Clearing organisations does not orphan the user

- **WHEN** a platform-admin or Verleiher-admin updates a member or organisation-admin under Verleiher V to `organisation_ids: []`
- **THEN** the user’s `hire_company_id` remains V
- **AND** the user remains listed under Verleiher V

#### Scenario: Demotion keeps home Verleiher

- **WHEN** a tenant_admin of Verleiher V is changed to role `member` or `organisation_admin` under Verleiher V
- **THEN** the user’s `hire_company_id` remains V
- **AND** the user remains listed under Verleiher V without requiring organisations

### Requirement: Role-scoped user visibility

The system SHALL list users for the active Verleiher according to the actor’s role. Platform-admins and Verleiher-admins SHALL see users belonging to the active Verleiher via home Verleiher (`hire_company_id`) or organisation membership under that Verleiher. Organisation-admins SHALL see only users who share at least one of their administered organisations. Listing MUST remain scoped to the active Verleiher (including for platform-admins); the system MUST NOT expose a global unscoped user directory in this change.

#### Scenario: Platform-admin sees Verleiher users including unassigned

- **WHEN** a platform-admin lists users with active Verleiher V
- **THEN** the response includes members and organisation-admins with `hire_company_id` V even if they have no organisations
- **AND** the response does not include users whose only home Verleiher is a different hire company

#### Scenario: Verleiher-admin sees own Verleiher users including unassigned

- **WHEN** a Verleiher-admin of V lists users
- **THEN** the response includes members and organisation-admins with home Verleiher V and no organisations
- **AND** the response does not include users of another Verleiher

#### Scenario: Organisation-admin sees only shared-organisation users

- **WHEN** an organisation-admin lists users
- **THEN** the response includes only users who share at least one administered organisation
- **AND** users with home Verleiher V but zero organisations are not included

#### Scenario: Cross-tenant isolation preserved

- **WHEN** a Verleiher-admin of B attempts to update, delete, or attach a member whose home Verleiher is A (and who has no organisations under B)
- **THEN** the system denies the operation (not found or not allowed for Verleiher)

### Requirement: Backfill home Verleiher from organisations

The system SHALL backfill `hire_company_id` for existing `member` and `organisation_admin` users that have null `hire_company_id` when their organisation links resolve to exactly one Verleiher. The system MUST NOT invent a Verleiher for users with no organisations, MUST NOT overwrite an existing `hire_company_id`, and MUST NOT set `hire_company_id` on platform admins via this backfill.

#### Scenario: Member with one Verleiher via organisations is backfilled

- **WHEN** a member has `hire_company_id` null and is linked only to organisations under Verleiher V
- **AND** the home-Verleiher backfill runs
- **THEN** the member’s `hire_company_id` becomes V

#### Scenario: Orphan without organisations is not invented a Verleiher

- **WHEN** a member has `hire_company_id` null and no organisations
- **AND** the home-Verleiher backfill runs
- **THEN** the member’s `hire_company_id` remains null
