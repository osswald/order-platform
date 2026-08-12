## Why

The cloud admin rentals calendar (`/rentals`) sits flush against the main content edges while every other Verwaltung page uses the shared `.vq-page` inset. That makes Ausleihe look unfinished next to Appliances, Lendings, and similar screens.

## What Changes

- Apply the shared cloud admin page chrome (`.vq-page`) to the rentals calendar root so horizontal and vertical insets match other pages.
- Remove the calendar’s local near-zero padding that currently overrides the shared inset.
- Optionally align the title row with `.vq-page-header` so header typography and spacing match list/dashboard pages (without wrapping the calendar in `ListDetailLayout` panel/card chrome).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `rental-calendar`: Require the rentals calendar surface to use the shared cloud admin page inset (same as other Verwaltung pages), not flush main-content edges.

## Impact

- Cloud frontend only: `RentalsCalendar.vue` (and possibly a small assertion in `RentalsCalendar.spec.ts`).
- No API, backend, routing, or i18n changes.
- No change to calendar/fleet interaction behavior — layout chrome only.
