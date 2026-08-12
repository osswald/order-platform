## Context

See proposal.md for motivation. Today:

- `ApplianceLending` is the only booking row: `appliance_id`, `organisation_id`, inclusive UTC `start_date`/`end_date`, optional `returned_at`. No parent, no label, no `hire_company_id`.
- Hire-company UI already *feels* like a rental: `OrganisationLendingDialog` picks one range + many appliances, then posts N independent `POST /appliances/{id}/lendings`. `Appliances.vue` posts a single-device lending.
- Overlap is enforced per appliance; edge sync and printer-event validation key off open lendings, not a group.
- Org users get a read-only `/appliance-lendings` list. Appliances live under Verwaltung with `tenantAdminOnly` / `canAccessTenantAdmin` (tenant_admin, or platform_admin with active Verleiher).
- Events (`Event.start`/`end`) are a separate POS timeline; first-event wizard must not wait on hardware.

## Goals / Non-Goals

**Goals:**
- Add a `Rental` row as the booking envelope; keep `ApplianceLending` as the occupancy/edge fact.
- One tenant-admin API family for rentals + assign/unassign, used by calendar, org dialog, and appliance detail.
- Calendar/fleet as custom Vue (no FullCalendar / paid resource timeline).
- Backfill so every existing lending has a rental before `rental_id` is NOT NULL.

**Non-Goals:**
- Rental↔event FK or UI linking
- Per-device date windows inside a rental
- Anonymous quantity holds (“2 servers, any”)
- Replacing org-facing lending lists
- New frontend calendar library
- Changing edge pairing/sync contracts

## Decisions

### 1. `rentals` table + required `appliance_lendings.rental_id`

**Choice:** New `rentals` (`hire_company_id`, `organisation_id`, `start_date`, `end_date`, `label` nullable). `appliance_lendings.rental_id` NOT NULL FK. Denormalize `hire_company_id` on the rental (must match the org’s Verleiher) so tenant list/calendar queries do not depend on joining organisations for isolation.

**Why:** Org already implies tenant, but platform admins switch Verleiher via `X-Hire-Company-Id`; listing “all rentals for active tenant” is the calendar’s primary query. Lendings keep `organisation_id` so edge and existing org list endpoints stay simple.

**Alternatives:** Only `organisation_id` on rental (extra join, easy to leak if a query forgets the org→tenant filter); treat rental as a view over identical lendings (cannot represent empty rentals).

### 2. Device dates are a copy of the rental window

**Choice:** On assign and on rental date PATCH, set lending start/end = rental start/end. Returned rows are frozen. Overlap check stays the existing inclusive open-lending query.

**Why:** Empty-first container owns the commitment; per-device windows are a later product. Early return already exists and does not need a shorter planned window.

**Alternatives:** Lending dates independent (calendar bars disagree); only store dates on rental and derive lending range (breaks historical return + current overlap SQL that reads lending columns).

### 3. Replace orphan create with rental-centric APIs

**Choice:** New router, e.g. `/rentals`:

| Method | Path | Role |
|--------|------|------|
| GET | `/rentals?from=&to=` | tenant admin; calendar range |
| GET | `/rentals/fleet?year=&month=` | tenant admin; appliances + overlapping open lendings |
| GET | `/rentals/{id}` | tenant admin |
| POST | `/rentals` | create; optional `appliance_ids` |
| PATCH | `/rentals/{id}` | label and/or dates |
| DELETE | `/rentals/{id}` | empty, or cancel when no *current* open lending |
| POST | `/rentals/{id}/appliances` | assign `{ appliance_id }` |
| DELETE | `/rentals/{id}/lendings/{lending_id}` | unassign planned or return current (reuse existing segment rules) |

`POST /appliances/{id}/lendings` becomes: body MUST include `rental_id` (assign into existing) **or** the appliance UI calls `POST /rentals` with that one id. Prefer the latter for the one-off form so the client does not invent a rental id. Reject bodies that omit `rental_id` if the old endpoint is kept as a compatibility shim.

**Why:** One write path; partial multi-assign is a rental with some children, not N unrelated rows.

**Alternatives:** Keep posting N lendings and infer groups in the UI (empty rentals impossible; grouping is heuristic).

### 4. Delete / cancel rules

**Choice:** DELETE allowed when there is no open lending with `start_date <= today` and `returned_at IS NULL`. Planned children are deleted with the rental; returned children are detached or deleted only if we choose cascade — **keep returned lendings** by blocking delete when any lending exists except we allow cancel of *planned-only* rentals (delete planned rows + rental) and delete of *empty* rentals. Rentals that only have returned (past) lendings: treat as history; do not delete in v1 (avoids orphaning history vs rewriting org past lists).

**Why:** Matches “current kit is out, you must return first” and keeps past occupancy for the org list.

**Alternatives:** Soft-delete `cancelled_at` on rental (more UI states); cascade-delete everything (loses history).

### 5. Backfill: one rental per legacy lending

**Choice:** Alembic data migration: for each `appliance_lendings` row, insert a rental (org, dates, `hire_company_id` from org, `label=NULL`) and set `rental_id`. Do **not** merge same-org-same-dates groups in v1.

**Why:** Safe, reversible mentally, no accidental merge of two coincidental bookings. Operators can later merge by hand if we add it.

**Alternatives:** Cluster by `(organisation_id, start_date, end_date)` (usually nicer calendars, sometimes wrong).

### 6. Calendar UI: one route, three modes, no new calendar SDK

**Choice:** Route e.g. `/rentals` (`tenantAdminOnly`), Verwaltung item next to Geräte. Nav copy: **Ausleihe** (de) / **Lending** (en), i18n key `nav.rentals`. Distinct from the org-facing Hauptmenü item **Geräteausleihen**. Toggle: month | year | fleet. CSS/grid Vue components:

- Month: 7-column month grid; rental bars as absolutely positioned or colspan chips using display name.
- Year: 12 month columns (or 12 stacked month strips) with horizontal bars.
- Fleet: sticky Y-axis (type headers + appliance names), day columns, occupancy bars. Exclude `is_hosted_virtual`.

Empty vs filled: outline/muted bar vs solid (or dashed vs filled). Color by organisation (stable hash of org id) so same customer is recognizable across views.

**Why:** FullCalendar’s resource timeline is premium; Vuetify date pickers are not a planner. A dedicated page is clearer than stuffing this into `Appliances.vue`.

**Alternatives:** FullCalendar (bundle + license for the useful view); three nav items (noisy).

### 7. Existing hire-company create UIs call the new API

**Choice:** `OrganisationLendingDialog`: `POST /rentals` with dates + `appliance_ids` (empty list allowed if we add “create rental” without devices from Organisations — calendar is the empty-first path; dialog may keep requiring ≥1 device or gain an optional list). `Appliances.vue` lend form: `POST /rentals` with one appliance. Org-facing `ApplianceLendings.vue` stays GET-only.

**Why:** No second mental model for operators; calendar is the empty-container entry.

### 8. Display name is computed, not stored

**Choice:** API includes `display_name` (label.strip() or organisation.name) plus `label` and `organisation_name`. UI never writes org name into `label`.

**Why:** Org rename stays consistent; labelled rentals stay labelled.

## Risks / Trade-offs

- **[Backfill duplicates calendar bars]** → Same-org same-weekend kit becomes N rentals instead of one. Mitigation: one-per-lending is correct-if-ugly; optional later merge. Do not auto-merge.
- **[Date PATCH vs overlap]** → All-or-nothing update in one transaction. Mitigation: return existing `lending_overlap` style error naming the blocking appliance.
- **[Partial assign from dialog]** → Today some devices can succeed and others fail. Mitigation: `POST /rentals` with `appliance_ids` is transactional: all assign or none; rental-only create is a separate call.
- **[Fleet height]** → Tens of appliances is fine; hundreds need virtualization later. Mitigation: v1 no virtualization; reuse type grouping as the scan aid.
- **[Org list still device-centric]** → After backfill, three devices on one weekend may still show as three past rows unless we later group by `rental_id`. Mitigation: out of scope; optional small group-by in a follow-up.
- **[Onboarding `appliance_lending` task]** → Still counts open lendings, not empty rentals. Mitigation: leave as-is (hardware still not assigned). Empty rental is a Verleiher planning object, not “kit lent.”

## Migration Plan

1. Add `rentals` (nullable unused) and nullable `appliance_lendings.rental_id`.
2. Backfill one rental per lending; set FKs.
3. Alter `rental_id` to NOT NULL; index `(hire_company_id, start_date, end_date)` and `(organisation_id, start_date)`.
4. Deploy API + UI that only write via rentals.
5. Export OpenAPI and regenerate `cloud/frontend` types in the same PR.

**Rollback:** If needed before NOT NULL, drop the column and table. After NOT NULL + app deploy, roll back the app first (old app cannot insert `rental_id`); do not drop the table out from under a mixed fleet.

**Edge/Pi:** No migration. Open lending for today is unchanged.

## Open Questions

- Whether `OrganisationLendingDialog` allows zero appliances (empty create from org page) or stays “must pick kit”; calendar already covers empty create.
