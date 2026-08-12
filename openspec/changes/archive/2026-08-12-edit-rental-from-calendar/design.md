## Context

See proposal.md for motivation. Current state:

- `RentalsCalendar.vue` month day cells and year rows open **create**; rental chips/bars are not clickable for edit (clicks bubble to create).
- Backend already exposes `GET`/`PATCH`/`DELETE` `/rentals/{id}`, `POST …/appliances`, `DELETE …/lendings/{lending_id}`. `RentalUpdate` allows label + dates only (no `organisation_id`). Delete rules match the rental-containers spec (empty OK; planned-only cancel OK; current open lending blocks delete; returned-history rentals are not deleted in v1).
- List `GET /rentals?from=&to=` already returns `lendings` with `segment`.

## Goals / Non-Goals

**Goals:**
- Month/year bar click → edit dialog (stop create bubble).
- Edit: label, dates, read-only org, device list with unassign/return, delete when allowed.
- Clear API error surfacing (overlap on date change; delete forbidden).

**Non-Goals:**
- Fleet busy-cell edit
- Changing organisation
- Drag-resize calendar bars
- New backend resources or schema migrations
- Dedicated `/rentals/:id` route (dialog on calendar is enough for this change)

## Decisions

### 1. Dialog on calendar, not a detail route

**Choice:** Extend (or sibling) the existing create dialog into create vs edit modes on `/rentals`.

**Why:** Operators already live on the calendar; a route would add nav chrome without much benefit for a medium editor.

**Alternatives:** `/rentals/:id` list-detail pattern (heavier); bottom sheet (less consistent with create).

### 2. Prefer `GET /rentals/{id}` when opening edit

**Choice:** On bar click, fetch `GET /rentals/{id}` to populate the dialog (fresh lendings/segments), falling back to list cache only if the GET fails after showing an error.

**Why:** List range responses can be stale after assign elsewhere; delete/unassign need accurate segments.

**Alternatives:** Use list payload only (faster, riskier).

### 3. Click handling: stopPropagation on bars

**Choice:** Rental chips (month) and year bars are buttons that call `openEdit(rentalId)` and `stopPropagation`. Empty day/track still calls `openCreate`.

**Why:** Fixes the create-vs-edit conflict without restructuring the grid.

### 4. Device actions reuse existing endpoints

**Choice:** Planned → `DELETE /rentals/{id}/lendings/{lending_id}` (deletes). Current → same endpoint (marks returned). Assign additional device via existing assign API from the edit dialog (picker of lendable free appliances optional in v1 — at minimum show list + unassign/return; “add device” can reuse a simple appliance select if low cost).

**Why:** Matches medium scope; no new APIs.

**Alternatives:** Read-only device list without actions (too thin for “medium”).

### 5. Delete button gated client-side, enforced server-side

**Choice:** Show Delete/Cancel when the loaded rental has no current open lending (i.e. empty, planned-only, or — if API still rejects returned-history — hide or show disabled with message). Always rely on API errors for the final gate.

**Why:** Existing `delete_rental_if_allowed` is the source of truth.

### 6. Organisation displayed read-only

**Choice:** Show organisation name as text; no select in edit mode. Create mode keeps the select.

**Why:** Locked product decision; API cannot PATCH org anyway.

## Risks / Trade-offs

- **[Date change overlap]** → Show API error; leave form open with previous saved values after failed PATCH (reload from GET on failure).
- **[Returned-history delete]** → If API rejects delete when only returned lendings exist, button must not promise success; prefer hiding delete unless empty or planned-only (mirror server rule in UI helper).
- **[Dense month chips]** → Multiple bars per day: each chip is independently clickable; hit targets stay chip-sized (acceptable for v1).
- **[Year bar click vs row create]** → stopPropagation on year-bar; clicking empty track still creates for that month.

## Migration Plan

1. Frontend-only deploy after tests.
2. No DB migration.
3. Rollback: revert frontend; APIs unchanged.

## Open Questions

_(none — scope locked: medium editor, month+year only, org immutable, delete when allowed)_
