## Context

Cloud event detail (`Events.vue` + `EventConfiguration.vue`) currently has three save modes on one screen:

1. **Stammdaten** (name, dates, payment flags, status) — manual Save → full PUT `/events/{id}` → `goToList()`
2. **Configuration** — `useEventConfigurationAutosave` → debounced PUT `/events/{id}/configuration` (paused while loading / layout cell dialog / cells loading)
3. **Receipts / stock** — separate autosave silos feeding `EventSaveStatusBar`

`EventStatusStepper` confirms a transition then only emits `update:modelValue`, so status becomes part of stammdaten dirty state and is easy to leave unsaved. `EventUpdate` on the backend already accepts partial bodies including `{ status }` alone and enforces transitions (including test→prod purge).

## Goals / Non-Goals

**Goals:**

- Persist status immediately after confirm, with a status-only payload; leave other unsaved stammdaten fields alone.
- Keep the operator on the event after create and edit stammdaten save (create → new detail route).
- Make debounced autosave resume when re-enabled while dirty so paused silos do not stick forever.

**Non-Goals:**

- Autosaving non-status stammdaten fields (Save button remains for those).
- Backend API or OpenAPI changes.
- Splitting or further optimizing configuration PUT payload size (covered by `event-configuration-perf`).
- Changing allowed status transition graph or prod purge semantics.

## Decisions

### 1. Status save is a dedicated action, not a flush of stammdaten

**Choice:** On confirm, call `PUT /events/{id}` with `{ status: next }` only. Do not include other form fields and do not clear unrelated stammdaten dirty state.

**Why:** Operators may have edited name/dates without intending to commit them with a lifecycle transition. Status is a workflow step; other fields stay on Save.

**Alternatives considered:**

- Flush full stammdaten on confirm — rejected (user: only status should change).
- Optimistic local status + deferred save — rejected (confirm must mean persisted).

**UX details:**

- Prefer **save-then-commit UI**: keep dialog open (or show saving) until PUT succeeds; then set `form.status`, `originalStatus`, and adjust stammdaten baseline for the status field only (so other dirty fields remain dirty).
- On failure: leave stepper on previous status, surface error message; do not advance `originalStatus`.

### 2. Stay on detail after create/edit save

**Choice:** Remove `goToList()` from successful `saveEvent` edit path. On create success, `goToDetail(created.id)` and apply the created event to the form (same as copy flow).

**Why:** Matches operator expectation after save and status change; list remains reachable via Back.

**Alternatives considered:** Toast + list — rejected by product decision.

### 3. Harden `useDirtyAutosave` for enable/disable

**Choice:** Watch the resolved `enabled` signal. When it transitions from false→true and `isDirty`, call `scheduleSave()` (or `flush()` if a save was suppressed while disabled). Keep existing debounce and in-flight coalescing (`pendingAfterSave`).

**Why:** Config autosave disables during layout cell loading/dialog; today nothing restarts the timer when enabled returns, so dirty state can hang until another edit.

**Alternatives considered:**

- Always leave autosave enabled and ignore dialog — riskier (partial/mid-edit payloads).
- Only fix call sites in `EventConfiguration` — weaker; stock/receipts share the same composable.

**Leave behavior (pragmatic):** On component unmount, clear debounce without auto-PUT (avoid orphan requests). Rely on existing `beforeunload` for tab close. Optionally flush on in-app route leave in a follow-up if tests show loss; not required for the minimum stability fix.

### 4. Status dirty accounting in the status bar

**Choice:** While a status PUT is in flight, treat aggregate save status as `saving` (or a dedicated busy state on the stepper). After success, status is not part of stammdaten dirty unless other fields differ. Do not show perpetual “unsaved” solely because the operator confirmed a status that already persisted.

**Implementation sketch:** Either exclude `status` from stammdaten dirty comparison once `originalStatus` tracks server, or update baseline status atomically with `originalStatus` after successful status PUT (preferred — keeps one snapshot helper).

## Risks / Trade-offs

- **[Risk] Race: operator edits stammdaten while status PUT in flight** → Mitigation: disable stepper confirm / block concurrent status transitions while status save busy; stammdaten Save remains independent.
- **[Risk] Prod transition still destructive** → Mitigation: keep existing confirm copy; only change when persistence happens (after confirm, immediately).
- **[Risk] Watching `enabled` causes a save mid-dialog close with incomplete cell edit** → Mitigation: keep autosave disabled while `cellDialogOpen` / cells loading; only resume after those gates clear (current gates stay).
- **[Trade-off] Three save modes remain** (manual stammdaten / immediate status / autosave silos) → Acceptable for this change; document in help if needed. Full stammdaten autosave is a future change.

## Migration Plan

- Frontend-only; deploy with normal cloud frontend release.
- No data migration; no feature flag required.
- Rollback: revert frontend PR; backend behavior unchanged.

## Open Questions

- None blocking — failed status save reverts UI (decision above). Flush-on-route-leave deferred unless QA finds remaining loss after enable-watch fix.
