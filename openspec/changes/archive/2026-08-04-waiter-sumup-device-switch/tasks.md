## 1. Tests first

- [x] 1.1 Extend `WaiterHubView` tests: when waiter session has a SumUp reader and multiple bundle readers exist, hub shows the label and a switch control
- [x] 1.2 Add test: choosing another reader updates waiter session (`sumupReaderId` / label) without calling shift-end or navigating to login
- [x] 1.3 Add test: switch control is hidden when fewer than two readers (or `sumup_connected` not needed); label still shown when bound and event allows connected pay

## 2. Hub UI

- [x] 2.1 On `WaiterHubView`, resolve current reader label from session + bundle; display it in the hub subtitle area when applicable
- [x] 2.2 Add **SumUp-Gerät wechseln** flow (picker matching login list pattern) when `readers.length > 1` and connected pay applies
- [x] 2.3 On pick, `setWaiter` with updated id/label only; keep shift and route on hub

## 3. Verify

- [x] 3.1 Run `cd pi/frontend && npm test` (or project Vitest target covering hub) and fix failures
- [x] 3.2 Run `./scripts/lint.sh --staged` (or full lint for touched paths) before commit
