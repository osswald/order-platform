## Why

On kitchen tablets (especially after immersive fullscreen), order tickets were too large: only ~2 columns fit where operators expect about four side-by-side. Browser zoom at 80% produced the right density; the app should match that without requiring manual zoom.

## What Changes

- Apply ~80% CSS zoom on the kitchen monitor root, with width/height compensation so the UI still fills the viewport.
- Slightly tighten horizontal column gap (8px → 6px) and keep column layout math in sync with that gap.
- Document/test that tablet landscape (~1024 CSS px) under 80% zoom fits at least four ticket columns.

## Capabilities

### New Capabilities

- `kitchen-monitor-layout`: Kitchen Bestellungen column density, zoom, and horizontal spacing for wall/tablet monitors.

### Modified Capabilities

- (none)

## Impact

- Pi frontend: `KitchenMonitorView.vue`, `KitchenOrderColumns.vue`, `kitchenMonitorHelpers.ts`, related tests.
- No Android native, cloud, or API changes.
