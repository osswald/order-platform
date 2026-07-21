## Why

Opening a kitchen monitor URL on the Pi (`/kitchen/:printerSlug`) redirects to the Events page instead of showing the display. Staff copy or open those URLs for kitchen tablets; today the link is not self-contained, so a new tab or reload cannot restore the selected event and the router guard sends them away.

## What Changes

- Make kitchen monitor URLs self-contained by including the event context (so copy/open/reload works without a prior waiter/register session).
- Restore `selectedEventId` from that URL context before the `requiresEvent` guard rejects navigation.
- Update admin ops “URL kopieren” / “Monitor öffnen” to generate the new URL shape.
- Add regression tests for cold navigation to kitchen without an in-memory event selection.
- Optionally apply the same shareable-URL pattern to other fullscreen display routes that share the bug (`pickup`, register customer display) if they are opened the same way from admin ops.

## Capabilities

### New Capabilities

- `pi-kitchen-monitor-routing`: Pi kitchen (and related fullscreen display) routes are bookmarkable/shareable: navigating to a monitor URL with valid bundle data lands on the monitor for the intended event, without first visiting Events or holding a waiter/register session.

### Modified Capabilities

- (none)

## Impact

- **Pi frontend**: `router` (kitchen route + guards), `useAdminOperations` URL builders / open helpers, possibly `sessions` or a small restore helper, kitchen/admin ops tests.
- **No backend / API / OpenAPI changes** expected (event id already exists in the local bundle).
- **Ops UX**: Existing copied kitchen URLs without event context will keep redirecting to Events until regenerated; document that URLs must be re-copied after the fix.
