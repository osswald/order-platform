## 1. Autosave stability

- [x] 1.1 Add failing tests in `useDirtyAutosave.test.ts` for: dirty + `enabled` false→true resumes `scheduleSave` / save without a further edit; debounce coalescing when enabled still holds
- [x] 1.2 Implement `enabled` watch (and any needed enable-resolution) in `useDirtyAutosave` so re-enable while dirty schedules a save
- [x] 1.3 Run cloud frontend unit tests for the composable and fix regressions

## 2. Status-only persist on confirm

- [x] 2.1 Add failing tests for status confirm → status-only PUT, stay on detail, failure reverts stepper, other dirty stammdaten unchanged (component or extracted helper tests as fits existing patterns)
- [x] 2.2 Wire `EventStatusStepper` / `Events.vue` so confirm triggers status-only `PUT /events/{id}`, updates `originalStatus` + status portion of stammdaten baseline on success, shows error and keeps previous status on failure
- [x] 2.3 Ensure concurrent status transitions are blocked while a status save is in flight; status bar / stepper reflects saving vs dirty correctly after success

## 3. Stay on event after create/edit save

- [x] 3.1 Add/adjust tests: successful edit save does not navigate to list; successful create navigates to new event detail
- [x] 3.2 Change `saveEvent` to stay on detail after edit and `goToDetail(created.id)` (+ apply form) after create; keep Back for returning to the list

## 4. Docs and verification

- [x] 4.1 Update help/i18n only if copy still implies Save is required for status changes
- [x] 4.2 Run cloud frontend tests (`npm test`) and typecheck; run `./scripts/lint.sh --staged` (or full lint) before commit
