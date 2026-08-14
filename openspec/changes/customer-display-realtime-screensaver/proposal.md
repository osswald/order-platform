## Why

Cash-register customer displays feel laggy (1s poll) and have layout/UX gaps during overflow, SumUp terminal payment, and multi-pickup success. Idle screens only show a static welcome line — organisations want branded gallery images that sync efficiently to the Pi without re-downloading unchanged assets or leaking across rentals.

## What Changes

- Push customer-display updates over a **WebSocket** from the Pi (register still `PUT`s display state; display subscribes instead of relying on 1s polling alone).
- Fix horizontal jump when order lines overflow the viewport (stable horizontal layout / scrollbar gutter).
- When payment type **sumup_connected** is chosen, show: `Bitte Anweisungen am Zahlungsterminal folgen.`
- When **Twint is cancelled** or **SumUp connected fails/is aborted**, restore the customer display to the **ordering (cart) view** — do not leave Twint QR or terminal-waiting screens stuck.
- After payment succeeds: keep `Danke!`; show **all** pickup codes as **badges**; copy `Bitte Abholbon mitnehmen` (1 code) / `Bitte Abholbons mitnehmen` (2+).
- Org-level **screensaver gallery** (max 10 images) in cloud admin; idle customer display rotates those images (fallback: Herzlich Willkommen).
- Pi sync: download each image **once** by content hash; skip if already present; **delete** when removed from gallery; **wipe** gallery store on org/appliance change and unpair.
- Android immersive fullscreen for customer display is already shipped — **out of scope**.

## Capabilities

### New Capabilities

- `customer-display-realtime`: WebSocket push for register display state, SumUp terminal waiting UI, Twint/SumUp abort restore to cart, stable overflow layout, multi-pickup success badges and Abholbon(s) copy.
- `customer-display-screensaver`: Organisation gallery (≤10 images), content-addressed Pi sync (download-once / GC / wipe on org change), idle playback on customer display.

### Modified Capabilities

- (none)

## Impact

- **Pi backend**: WebSocket endpoint for register display; broadcast on `PUT` display; local content-addressed screensaver store; sync/lifecycle hooks (manifest pull, GC, org-change wipe via `reconcile_bundle_lifecycle` / unpair).
- **Pi frontend**: `RegisterDisplayView` (states, layout, badges, screensaver); register pay hooks for `sumup_connected`; display WS client.
- **Cloud backend/frontend**: Org gallery CRUD (upload/delete, max 10); edge bundle **manifest** (hashes, not image bytes); download API for missing hashes. Display rotation order is unspecified.
- **Sync**: Bundle carries screensaver manifest only; binary transfer is separate and conditional.
- No change to Android immersive bridge; no **BREAKING** API removals (additive WS + gallery).
