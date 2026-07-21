## Why

On iPad Safari (observed on iPadOS 16.7.6), kitchen monitor ticket actions **Teildruck** and **Komplettdruck** render as oversized color/outline blocks with no visible labels. Chrome on desktop looks fine; kitchen header controls on the same iPad are fine. Kitchen staff cannot reliably tell the buttons apart or confirm they are usable.

## What Changes

- Fix ticket-footer action button layout so labels stay visible and buttons fit within the ticket width on WebKit/Safari (including older iPadOS 16).
- Constrain CSS Grid/`<button>` shrink behavior for the two-column action row (allow shrink/wrap; avoid intrinsic overflow clipped by the ticket card).
- Keep labels, semantics, and print behavior unchanged (same German labels and emit handlers).

## Capabilities

### New Capabilities

- `kitchen-ticket-actions`: Requirements for kitchen order-ticket action controls (partial/complete print) remaining readable and usable within the ticket column on touch Safari and desktop browsers.

### Modified Capabilities

- (none)

## Impact

- **Pi frontend:** `KitchenTicketColumn.vue` styles (and possibly shared `.btn` overrides scoped to ticket actions only).
- **Tests:** Frontend coverage for action-row CSS constraints / component render of both labels (Vitest + existing kitchen component test patterns).
- **No** backend, API, or OpenAPI changes.
