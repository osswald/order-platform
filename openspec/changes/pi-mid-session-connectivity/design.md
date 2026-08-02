## Context

See proposal.md for motivation. Today Pi reachability is probed only in `App.vue` on cold start via `probeApiBase()` (`GET /health`, Android native bridge). Register/waiter sessions persist in `localStorage` with no idle timeout. Bundle refresh runs every 60s while visible but swallows failures. Money-path CTAs navigate locally without probing.

Constraints:
- Reuse existing probe (2.5s timeout / Android bridge) — no new backend endpoints
- Soft recovery mid-session (preserve session); hard redirect to connection-setup remains startup-only
- Pi frontend Vue 3 patterns: composables + small reactive store modules

## Goals / Non-Goals

**Goals:**
- Single shared connectivity state consumed by hubs and gated actions
- Detect unreachable Pi on resume and via 30s keepalive while visible
- Soft banner with retry + optional connection-setup escape
- Gate register/waiter money-path navigations until reachable (or recently confirmed)

**Non-Goals:**
- Changing cold-start probe / connection-setup redirect semantics
- Offline order queue or optimistic local order creation
- Idle logout / session expiry
- Kitchen monitor, admin hub, or customer display as primary surfaces for this banner (may share state later)
- Adding request timeouts to all `piFetch` calls (separate concern)

## Decisions

### 1. Shared `usePiConnectivity` + thin reactive store

**Choice:** Module-level reactive state (`status`, `lastOkAt`, `probing`) with `ensureReachable({ force? })`, `probeNow()`, and lifecycle helpers for resume/keepalive. Expose via composable.

**Alternatives considered:**
- Probe ad hoc in each view — duplicates debounce/banner logic
- Derive only from bundle refresh failures — conflates sync/data errors with reachability; slower fail signal

**Rationale:** One brain, many consumers; tests can drive state without mounting full hubs.

### 2. Soft banner, not auto-redirect

**Choice:** When unreachable mid-session, show an inline banner (same visual language as waiter print-fail banner). Actions: “Erneut prüfen” (re-probe) and “Verbindung ändern” (navigate to connection-setup). Session and route stay put.

**Alternatives considered:**
- Auto `router.replace(connection-setup)` — matches startup but feels like logout; wrong default for WiFi naps
- Toast only — easy to miss; does not disable CTAs

### 3. Keepalive every 30s while visible; probe on `visibilitychange` → visible

**Choice:** Separate timer from `useBundleRefresh` (60s data sync). On become-visible, probe immediately; while visible, interval 30s. Stop timer when hidden.

**Alternatives considered:**
- Piggyback on bundle refresh — cheaper but weaker signal
- Always-on interval including background — wasted work; Android may suspend timers anyway

### 4. Warm window skips force-probe on CTAs

**Choice:** Gated actions call `ensureReachable()`. If `status === reachable` and `lastOkAt` within ~20s, return ok without a new probe. Otherwise probe (show brief “Prüfe Verbindung…” / disable CTA). On failure, stay on hub, ensure banner visible, do not navigate.

**Rationale:** Keepalive/resume keep state warm so taps stay snappy; force-probe covers races and stale-ok edge cases.

### 5. Money-path gate scope

**Register hub:** Neue Bestellung, Sammelrechnungen, resume open unpaid order.

**Waiter hub:** Neue Bestellung, Tisch abrechnen, Offene Tische, Sammelrechnungen. Also gate Stock (same failure mode when browsing inventory after idle).

**Deep links / intermediate screens:** Prefer gating at hub CTAs. If user is already mid-flow (e.g. on `table-new` or order screen) when connectivity drops, banner may not be on that screen in v1 — submit still fails with existing toasts. Optional follow-up: global shell banner.

### 6. Banner placement

**Choice:** Shared small component mounted on register hub and waiter hub first (where gated CTAs live). App-shell global banner is a follow-up if needed for mid-order screens.

## Risks / Trade-offs

- **[False unreachable on flaky WiFi]** → Single failed probe flips banner; “Erneut prüfen” and next keepalive can clear. Warm window avoids hammering on every tap.
- **[Probe adds latency on cold CTA after long idle]** → Bounded by existing ~2.5s probe timeout; better than hanging `piFetch` with no timeout.
- **[30s keepalive battery/network]** → Lightweight `/health` only while visible; acceptable for always-on venue tablets.
- **[User already on order screen when Pi dies]** → v1 does not block submit with the new gate; existing error toast remains. Document as known gap / follow-up.

## Migration Plan

- Frontend-only change; ship with normal Pi frontend deploy / Android WebView asset update.
- No data migration. Rollback = revert frontend; startup probe behavior unchanged.

## Open Questions

- Exact German copy for banner / retry / change-connection (can match existing connection-setup tone during implement).
- Whether Stock stays gated if product prefers browse-even-when-offline; currently included for consistency.
