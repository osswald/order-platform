## Context

See proposal.md — Why. Today the register POS mirrors cart/payment UI to Pi via `PUT /v1/registers/{uuid}/display` into `RegisterDisplayState`; `RegisterDisplayView` polls GET every 1s. Cart lines before Fertig live only in POS memory; the Pi holds a display snapshot. Twint already pushes a dedicated state; `sumup_connected` does not. Success already joins `pickup_codes` with commas. Receipt logos embed base64 in the edge bundle — unsuitable for a ≤10 full-screen gallery. Bundle reconcile already purges operational data when `organisation_id` / `appliance_id` changes (`reconcile_bundle_lifecycle`); unpair calls `purge_on_unpair`.

## Goals / Non-Goals

**Goals:**

- Sub-second customer-display updates via FastAPI WebSocket fan-out on existing PUT.
- Stable overflow layout; SumUp waiting copy; Twint cancel / SumUp fail restore cart; badge success UI with Abholbon(s) copy.
- Org gallery with content-addressed Pi media store (download-once, GC, wipe on org change/unpair).
- Idle gallery playback with welcome fallback.

**Non-Goals:**

- Changing Android immersive behavior (already shipped).
- Moving the live cart onto the Pi as an order before Fertig.
- Embedding screensaver bytes in the catalogue bundle (receipt-logo pattern).
- Socket.IO or cloud-hosted WebSockets (display talks to Pi on LAN).
- Event-level screensaver override (org-level only for this change).

## Decisions

### 1. WebSocket on Pi, keyed by cash register UUID

- **Choice:** Native FastAPI WebSocket (e.g. `WS /v1/registers/{cash_register_uuid}/display/ws?event_id=…`). In-process subscriber set; `put_register_display` broadcasts JSON payload (+ `updated_at`) after commit.
- **Why:** Display and POS are usually two LAN devices; Pi is already the shared store. No new broker.
- **Alternatives:** Faster poll / long-poll — simpler but noisier; Socket.IO — extra dependency; BroadcastChannel — same-browser only.

### 2. Keep HTTP PUT/GET; WS is push transport

- Writers unchanged (`useRegisterDisplay` / pay hooks).
- Display: connect WS, apply messages; optional slow GET only while disconnected.
- **Why:** Minimal change to POS; HTTP remains debug/fallback path.

### 3. Payment waiting states and abort restore

- Twint: `onTwintShow` already pushes `state: "twint"`; today `onTwintHide` is a no-op — implement it to re-push ordering payload (open lines + total) on cancel/confirm dismiss.
- SumUp: push `state: "sumup_connected"` when terminal collection starts; on failure/abort (and not on successful settle), re-push the same ordering snapshot.
- Successful settle continues to push `submitted` (unchanged path).
- Display renders dedicated panels for twint / sumup_connected with fixed German waiting copy for SumUp.
- **Why:** Same abort semantics for both payment types; avoids stuck QR/terminal screens.

### 4. Overflow layout

- Prefer CSS grid/columns for name vs amount plus `scrollbar-gutter: stable` (or overlay scrollbars) so scrollbar appearance does not shift the price column.

### 5. Success badges + plural copy

- Render each code in `pickup_codes` (else `[pickup_code]`) as a badge.
- Footer: singular vs plural Abholbon(s) by badge count.

### 6. Screensaver: manifest in bundle, blobs by hash

- Cloud: org-scoped table/blob store; upload/list/delete (no reorder); max 10; size/type limits.
- Edge bundle: `screensaver_images: [{ sha256, mime }, …]` only; order in the list is insignificant.
- Cloud edge: authenticated GET by hash for the credential’s organisation.
- Pi: files under a dedicated data dir keyed by sha256; sync after bundle pull — download missing, delete orphans vs manifest.
- Org/appliance change and unpair: wipe entire screensaver directory (even if a hash would match the next org — no cross-tenant leftovers).
- **Alternatives:** Base64 in bundle — rejected (bloat / re-transfer); event-level galleries — deferred.

### 7. Idle playback

- Display loads local URLs from Pi HTTP (e.g. `/v1/screensaver/{sha256}`) using current event/org context from bundle.
- Rotate when count > 1 (any stable local sequence is fine); dwell ~8–10s; leave immediately on non-idle state.

## Risks / Trade-offs

- **[Risk] Multi-worker Pi process** → Mitigation: single Uvicorn worker for edge (current typical deploy); document that WS fan-out is in-process.
- **[Risk] WS drops on tablet sleep** → Mitigation: auto-reconnect + one GET snapshot on open/reconnect.
- **[Risk] Large gallery fills SD card** → Mitigation: max 10 + per-image size cap; wipe on org change.
- **[Risk] Sync blocks on slow downloads** → Mitigation: download sequentially with timeouts; failed hash retried next cycle; display falls back to welcome until files exist.
- **[Trade-off] Gallery not in bundle** → Extra edge round-trips for new hashes only; worth it vs re-shipping every sync.

## Migration Plan

1. Deploy cloud gallery APIs + admin UI (empty gallery = no behavior change).
2. Deploy Pi WS + display client (HTTP poll still works during rollout).
3. Deploy screensaver sync + idle UI (no images → welcome unchanged).
4. Rollback: disable WS client (poll-only) or ignore empty manifest; local orphan files GC on next successful sync or unpair.

## Open Questions

- Exact per-image byte limit (suggest 2–5 MB) and whether WebP is allowed — finalize at implement time without changing requirements shape.
- Exact dwell/crossfade timing for multi-image idle — cosmetic; default 8–10s acceptable.
