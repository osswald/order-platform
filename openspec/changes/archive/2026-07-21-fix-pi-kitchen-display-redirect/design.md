## Context

Kitchen monitors are fullscreen Pi routes at `/kitchen/:printerSlug/:view?` with `meta.requiresEvent: true`. Admin Operations builds absolute URLs and opens them in a new tab (`window.open`) or copies them for kitchen tablets.

`selectedEventId` lives only in memory (and is restored only from waiter/register localStorage sessions). A new tab or a cold load of a kitchen URL therefore starts with `selectedEventId === null`. The router guard then redirects to `events`:

```ts
if (to.meta.requiresEvent && store.selectedEventId.value == null) {
  return { name: 'events' }
}
```

`openKitchen` sets `selectedEventId` in the *parent* tab before `window.open`, which cannot propagate into the new Vue app instance. Copied URLs omit event entirely.

## Goals / Non-Goals

**Goals:**

- Cold navigation to a kitchen monitor URL (new tab, paste, reload) lands on the monitor for the intended event when the bundle is ready and the event exists.
- Admin “URL kopieren” / “Monitor öffnen” produce/use that self-contained URL.
- Guard still sends users to Events when event context is missing or invalid.
- Regression tests cover kitchen cold-load behavior.

**Non-Goals:**

- Persisting a global “last selected event” for all Pi routes (waiter/order flows stay as today).
- Changing kitchen ticket/API contracts or printer slug rules.
- Redesigning the kitchen UI.
- Fixing unrelated bundle-not-ready redirects (already covered by existing guard behavior).

## Decisions

### 1. Encode event id in the kitchen URL via query `event`

- **Choice:** `/kitchen/:printerSlug/:view?event=<eventId>` (and keep optional view slug).
- **Why:** Shareable across tabs/devices; minimal path churn vs inserting a path segment; easy for admin URL builders; docs only need a query note.
- **Alternatives considered:**
  - Persist `selectedEventId` in its own localStorage key — helps same-browser reload, fails for copied URLs on another device, and couples display setup to ambient session state.
  - Path `/kitchen/:eventId/:printerSlug` — clearer but **BREAKING** for existing bookmarks and README patterns; higher churn for little gain.
  - Drop `requiresEvent` on kitchen and resolve event only inside the view — weaker: other code assumes `selectedEventId` / `useEventContext()`; easier to leave inconsistent.

### 2. Restore event in the router guard before `requiresEvent`

- **Choice:** When navigating to a route that needs an event, if `selectedEventId` is null and `to.query.event` is a valid id present in the loaded bundle, set `selectedEventId` then continue. Invalid/missing → keep redirect to `events`.
- **Why:** Single choke point; works for kitchen and can extend to other display routes with the same query later.
- **Alternatives considered:** Restore only inside `KitchenMonitorView` — too late; guard already redirected.

### 3. Scope: kitchen first; pickup/display same pattern if already URL-shared

- **Choice:** Implement kitchen end-to-end. Apply the same `?event=` builder + guard restore to `pickup` and `register-display` if admin ops already exposes open/copy URLs for them (same failure mode on reload/new tab).
- **Why:** Kitchen is the reported bug; shared guard logic keeps cost low for the siblings.

### 4. Do not remove `requiresEvent` from kitchen

- Kitchen still needs a selected event for `useEventContext` / order loading. URL restore satisfies the meta flag instead of weakening it.

## Risks / Trade-offs

- **[Stale bookmarked URLs without `?event=`]** → Still redirect to Events; ops must re-copy URLs after deploy. Acceptable; document in PR/README.
- **[Wrong event id in query]** → Guard redirects to Events (or could show an inline error later). Prefer Events for consistency with today.
- **[Setting `selectedEventId` from a display URL]** → May change which event is “selected” if the user later navigates to waiter flows in the same tab. Mitigation: display routes are fullscreen dedicated tablets; acceptable. Do not write a waiter/register session from this restore.
- **[Query vs path discoverability]** → Slightly less pretty URLs; prefer stability over aesthetics.

## Migration Plan

1. Ship frontend change (URL builders + guard + tests).
2. Re-copy kitchen URLs from Admin → Operations → Küchenmonitor on each venue Pi.
3. Rollback: revert frontend; old URLs without query continue to behave as today (redirect).

## Open Questions

- None blocking; pickup/register-display inclusion is a small same-PR decision during implement if open/copy helpers already exist.
