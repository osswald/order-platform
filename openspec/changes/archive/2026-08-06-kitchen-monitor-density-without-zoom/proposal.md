## Why

CSS `zoom: 0.8` with a 125% compensating width on the kitchen monitor fixed Bestellungen density on tablets, but broke Produkte wrapping (cards run off to the right under browser zoom) and pushed header controls (Bestellungen / Produkte / Aktualisieren) off the visible right edge on Android and desktop. We need the denser order columns without a fake-wide layout box.

## What Changes

- **Remove** kitchen-monitor CSS `zoom` and compensating `width` / `height`.
- Achieve ~four ticket columns on typical tablet landscape by lowering the minimum column width (and keeping the tighter column gap), optionally with a light kitchen-route font-size scale that does not change containing-block width.
- Restore Produkte flex-wrap against a true 100% viewport width and keep the kitchen header fully visible.
- Update `kitchen-monitor-layout` requirements to drop the zoom contract and require wrap-safe density instead.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `kitchen-monitor-layout`: Replace 80% CSS zoom requirements with density via column min-width (and optional font scale); require products wrap and header visibility within the real viewport.

## Impact

- Pi frontend: `KitchenMonitorView.vue`, `kitchenMonitorHelpers.ts` (+ tests), contract tests that assert zoom CSS.
- OpenSpec main spec `kitchen-monitor-layout` (on archive/sync).
- No Android native or backend API changes.
