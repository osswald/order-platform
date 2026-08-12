## Context

See proposal.md for motivation. Domain already requires `ApplianceLending.rental_id` (non-null); assign/unassign/return APIs exist on `/rentals`. Overlap today uses inclusive ranges (`start <= other.end AND end >= other.start`), so endpoint-touch (A ends D, B starts D) is rejected. Appliance detail and org Geräte lend paths call `POST /rentals/` with `appliance_ids` and never surface a rental picker. Lending list DTOs on appliance/org endpoints omit rental identity. Calendar edit can unassign/return but not add.

## Goals / Non-Goals

**Goals:**

- Single shared overlap rule: endpoint-touch allowed; multi-day interior overlap rejected; returned lendings never block.
- On a calendar day covered by more than one open lending for one appliance, resolve “active today” to the lending whose `start_date` equals that day when present; otherwise keep existing cover logic.
- Wire calendar edit to existing `POST /rentals/{id}/appliances`.
- Reuse one frontend rental-choice pattern (pick existing for org, or create-new) from appliance and org lend dialogs.
- Expose `rental_id` + display name on lending payloads used by appliance history and org lists; group UI by rental.

**Non-Goals:**

- Per-device date windows independent of the rental.
- Changing create-rental calendar dialog to pick devices.
- Redesigning org tab into a nested rentals tree (Option Y).
- Fleet busy-cell click-to-edit.
- Schema migration beyond DTO/OpenAPI (no DB column changes expected).

## Decisions

### D1 — Overlap uses exclusive endpoint touch

**Choice:** Two open lendings for the same appliance conflict iff `start_a < end_b AND start_b < end_a` (strict). Inclusive bars remain for display; only the conflict predicate changes. Apply the same predicate in `find_open_overlap`, appliance `lend_check_*`, and any date-move checks.

**Alternatives:** Half-open `[start,end)` occupancy — breaks one-day rentals (`start == end`). Keep inclusive conflict — fails the handover requirement.

### D2 — Active-today preference on handover day

**Choice:** When selecting the open lending that “covers” a given UTC day for status/edge (list active org, appliance status, etc.), if multiple open lendings satisfy `start <= day <= end`, prefer the one with `start_date == day` (the arriving rental). If several start that day, prefer the lowest `id` for stability. Fleet may still render both occupancy bars meeting on D.

**Alternatives:** Arbitrary `query.first()` — nondeterministic org for POS. Prefer ending rental — wrong for midday handover to the next customer.

### D3 — Membership-only “edit lending”

**Choice:** No PATCH of lending dates. Add = assign; edit UX = unassign/return only; dates always mirror rental (existing rule).

### D4 — Rental picker UX

**Choice:** Shared dialog/composable: list rentals for the chosen organisation (newest `start_date` first, then `id`); mark or disable rows that would conflict for the selected device(s) using lend_check or client-side application of D1; allow “create new rental” with dates + optional label; then `POST /rentals/{id}/appliances` (or create with `appliance_ids`). After success: toast only, stay on page. Org dialog keeps multi-select appliances after rental is chosen.

**Alternatives:** Pick-only (no create) — forces calendar-first workflow, rejected in explore. Always create — status quo.

### D5 — History / lists

**Choice:** Appliance history groups by `rental_id`, foldable sections, rentals ordered newest first (`start_date` desc, then `id` desc). Org Geräte table remains flat device rows with a rental column + past section; optional deep-link to `/rentals` with rental id when practical without large router work (link to Ausleihe is enough if query deep-link is costly — prefer including `rental_id` in UI state for a future deep-link).

### D6 — API shape

**Choice:** Extend appliance lending and org lending item schemas with `rental_id` and `rental_display_name` (computed via existing `rental_display_name`). Regenerate OpenAPI types. No new endpoints required if list rentals filtered by `organisation_id` is available or added as a query param on `GET /rentals/`.

**Alternatives:** Nested `/organisations/{id}/rentals` — nicer but extra surface; only add if `GET /rentals/?organisation_id=` is missing.

## Risks / Trade-offs

- [Two open lendings on D] → Edge must use D2; add regression tests for `no_active_lending_today` vs wrong org.
- [Same-day 15–15 + 15–15 both allowed] → Intentional under D1; operators can double-book one calendar day; mitigate with UI conflict hints when ranges are identical, not by re-blocking touch.
- [Fleet shows two bars on D] → Acceptable visual; do not invent half-day cells in this change.
- [Org list without deep-link] → Rental column still meets Option X; deep-link can follow.

## Migration Plan

- Deploy backend overlap + DTO changes with frontend in the same release (frontend depends on new fields).
- No data backfill; existing rows already have `rental_id`.
- Rollback: revert overlap to inclusive (stricter) is safe; reverting DTOs needs frontend rollback too.

## Open Questions

- None. `GET /rentals/` currently filters by optional `from`/`to` only — task 2.1 adds `organisation_id`.
