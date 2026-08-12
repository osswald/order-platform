## Context

See proposal.md. Product code for these behaviours is already on `main` (commits from keep-calendar-after-delete through packing PDF IP/type labels). This change only updates OpenSpec so living specs match production.

## Goals / Non-Goals

**Goals:**

- Fold shipped rental polish into `openspec/specs/` via delta specs, then archive.
- Prefer ADDED requirements where behaviour is new; MODIFIED where existing requirements are now inaccurate (e.g. Flotte naming, month chips, packing PDF Geräte row content).

**Non-Goals:**

- Re-implementing or changing application code.
- Spec’ing every pixel of Vuetify styling.
- Expanding Verleiher settings beyond the nav visibility fix.

## Decisions

### 1. One retroactive change covering the polish cluster

- **Choice:** Single change `rental-calendar-polish` instead of one change per commit.
- **Why:** Commits share the rental calendar / Zubehör / packing surface; one archive keeps history readable.
- **Alternatives:** Per-commit changes — more archive noise for already-shipped work.

### 2. New capability for Verleiher settings nav

- **Choice:** `verleiher-settings-nav` rather than stretching `rental-calendar`.
- **Why:** Nav gate is hire-company settings, not Ausleihe.

### 3. Tasks are sync/archive only

- **Choice:** Tasks mark “already shipped” + sync living specs + validate/archive.
- **Why:** No code left to write; the value is spec accuracy.

## Risks / Trade-offs

- [Spec drift if main already partially matches] → Diff carefully; ADDED vs MODIFIED as needed; keep archive idempotent on re-read.
- [Bundle unrelated platform-admin nav with rental polish] → Accepted; it shipped in the same window and otherwise has no home.
