## 1. Connectivity core

- [ ] 1.1 Write unit tests for mid-session connectivity state: probe success/failure, warm-window `ensureReachable`, resume probe, 30s keepalive start/stop on visibility
- [ ] 1.2 Implement reactive connectivity store + `usePiConnectivity` composable wrapping `probeApiBase` (status, `lastOkAt`, `probing`, `ensureReachable`, `probeNow`)
- [ ] 1.3 Wire resume + 30s keepalive into app shell (`App.vue` or dedicated composable mounted once); stop timer when document is hidden

## 2. Soft banner UI

- [ ] 2.1 Write component/view tests for unreachable banner: shown when unreachable, retry re-probes, “Verbindung ändern” navigates to connection-setup, session preserved
- [ ] 2.2 Add shared banner component (print-fail visual language) with German copy for unreachable / retry / change connection
- [ ] 2.3 Mount banner on register hub and waiter hub bound to connectivity status

## 3. Gate money-path actions

- [ ] 3.1 Write tests for register hub gates: Neue Bestellung, Sammelrechnungen, resume open order — block when unreachable; allow navigate when warm-ok; probe then navigate when stale
- [ ] 3.2 Write tests for waiter hub gates: Neue Bestellung, Tisch abrechnen, Offene Tische, Sammelrechnungen, Lagerbestand — same rules
- [ ] 3.3 Implement gated handlers on register hub (disable/busy while probing; no navigate on failure)
- [ ] 3.4 Implement gated handlers on waiter hub

## 4. Verification

- [ ] 4.1 Run Pi frontend tests (`cd pi/frontend && npm test`) and fix failures
- [ ] 4.2 Run staged lint (`./scripts/lint.sh --staged`) before commit
- [ ] 4.3 Confirm cold-start connection-setup path still redirects on startup probe failure (no regression)
