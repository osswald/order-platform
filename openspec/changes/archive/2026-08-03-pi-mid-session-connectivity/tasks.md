## 1. Connectivity core

- [x] 1.1 Write unit tests for mid-session connectivity state: probe success/failure, warm-window `ensureReachable`, resume probe, 30s keepalive start/stop on visibility
- [x] 1.2 Implement reactive connectivity store + `usePiConnectivity` composable wrapping `probeApiBase` (status, `lastOkAt`, `probing`, `ensureReachable`, `probeNow`)
- [x] 1.3 Wire resume + 30s keepalive into app shell (`App.vue` or dedicated composable mounted once); stop timer when document is hidden

## 2. Soft banner UI

- [x] 2.1 Write component/view tests for unreachable banner: shown when unreachable, retry re-probes, “Verbindung ändern” navigates to connection-setup, session preserved
- [x] 2.2 Add shared banner component (print-fail visual language) with German copy for unreachable / retry / change connection
- [x] 2.3 Mount banner on register hub and waiter hub bound to connectivity status

## 3. Gate money-path actions

- [x] 3.1 Write tests for register hub gates: Neue Bestellung, Sammelrechnungen, resume open order — block when unreachable; allow navigate when warm-ok; probe then navigate when stale
- [x] 3.2 Write tests for waiter hub gates: Neue Bestellung, Tisch abrechnen, Offene Tische, Sammelrechnungen, Lagerbestand — same rules
- [x] 3.3 Implement gated handlers on register hub (disable/busy while probing; no navigate on failure)
- [x] 3.4 Implement gated handlers on waiter hub

## 4. Verification

- [x] 4.1 Run Pi frontend tests (`cd pi/frontend && npm test`) and fix failures
- [x] 4.2 Run staged lint (`./scripts/lint.sh --staged`) before commit
- [x] 4.3 Confirm cold-start connection-setup path still redirects on startup probe failure (no regression)
