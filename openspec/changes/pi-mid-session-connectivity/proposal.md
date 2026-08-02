## Why

Android tablets often sit idle for minutes with a register or waiter still logged in. After WiFi sleep or an AP drop, the Pi can be unreachable while the UI still looks healthy — sessions live in `localStorage`, and Pi reachability is only probed on cold start. Staff then start or settle orders against a dead link and only learn at submit time.

## What Changes

- Add mid-session Pi reachability tracking (shared state + `/health` probe reuse)
- Probe when the app becomes visible again (Android wake / tab resume)
- Keepalive probe every 30s while the document is visible
- Soft unreachable UX: banner with retry and optional link to connection setup (no auto-redirect, session preserved)
- Gate money-path actions until Pi is reachable (or recently confirmed): new order, settle, open tables, collective bills, resume unpaid register orders
- Skip force-probe on gated actions when a recent successful probe exists (warmup window)

## Capabilities

### New Capabilities
- `pi-mid-session-connectivity`: Mid-session Pi reachability (resume + keepalive), soft banner recovery, and gating of register/waiter money-path actions

### Modified Capabilities
- _(none — startup hard-redirect behavior in `pi-connection-setup` is unchanged)_

## Impact

- **Pi frontend**: new connectivity composable/store, banner UI on register/waiter hubs, gated navigation on money-path CTAs, wire resume/keepalive from app shell
- **Reuse**: existing `probeApiBase()` / Android `AndroidNetwork.probeHealth` / `GET /health` — no backend API changes
- **Out of scope**: idle logout, offline order queue, changing cold-start connection-setup redirect, kitchen-monitor-specific flows
