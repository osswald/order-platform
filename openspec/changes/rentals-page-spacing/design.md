## Context

See proposal.md for motivation. Cloud admin page spacing is not applied in `App.vue`’s `.main-content`; each page opts into `.vq-page` from `vuetify-app.css` (`padding: 2rem 2rem 2rem 2.25rem`, `1rem` under 992px). Most Verwaltung pages get that via `ListDetailLayout`; standalone pages (Dashboard, HelpCenter, EventStatsPage) add `vq-page` on their root. `RentalsCalendar.vue` currently uses only `.rentals-calendar` with `padding: 0.25rem 0 2rem`, so horizontal inset is zero.

## Goals / Non-Goals

**Goals:**

- Match rentals calendar page inset to other cloud admin pages.
- Keep the calendar as a custom surface (no forced list/detail cards).

**Non-Goals:**

- Changing `App.vue` / global main-content padding for all routes.
- Refactoring rentals into `ListDetailLayout`.
- Changing calendar, fleet, or dialog behavior beyond chrome spacing.
- Restyling month/year/fleet grids for aesthetic reasons beyond the page inset.

## Decisions

### 1. Opt into `.vq-page` on the calendar root (not global shell padding)

- **Choice:** Add `vq-page` to the `RentalsCalendar` root element and remove the conflicting local padding on `.rentals-calendar`.
- **Why:** Matches the established pattern (Dashboard, HelpCenter) without changing every page or the app shell.
- **Alternatives considered:**
  - Pad `.main-content` in `App.vue` — would double-pad every existing `.vq-page` page; larger blast radius.
  - Wrap in `ListDetailLayout` — brings panel/card chrome unsuitable for a full-bleed calendar grid.

### 2. Optionally reuse `.vq-page-header` for the title row

- **Choice:** Prefer adding `vq-page-header` (and keeping existing header actions) so title size/spacing matches other pages; keep flex layout for Create + HelpLink.
- **Why:** Low cost consistency; if markup churn is awkward, `.vq-page` alone still satisfies the inset requirement.
- **Alternatives considered:** Leave custom `.rentals-header` styles only — acceptable if visual check shows spacing is enough.

### 3. Test approach

- **Choice:** Assert the root element includes the `vq-page` class (or equivalent shared chrome marker) in the existing `RentalsCalendar` mount tests; no visual regression suite required for this change.
- **Why:** Spec is about using shared chrome; class presence is a stable, cheap signal used elsewhere for layout contracts.

## Risks / Trade-offs

- [Double padding if local padding is left in place] → Remove `.rentals-calendar`’s top/side padding when adding `vq-page`; keep only layout (`flex`, `gap`) on the local class.
- [Calendar feels slightly narrower] → Acceptable; matches other pages by design. Wide month/fleet grids still use full available width inside the inset.

## Migration Plan

- Frontend-only CSS/class change; deploy with normal cloud frontend release. Rollback by reverting the component class/padding change.
