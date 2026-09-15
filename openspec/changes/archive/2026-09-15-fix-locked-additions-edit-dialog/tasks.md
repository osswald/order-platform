## 1. Regression tests (failing first)

- [x] 1.1 Add a Vitest case in `EventConfigLayoutsSection.spec.ts` that opens an existing combo cell with non-empty `locked_addition_ids`, loads Zusatz options, and asserts those ids remain selected on `cellEdit` / checklist state after flush — verify with `npm test` (or package script for that spec) failing or asserting the reopen seed today
- [x] 1.2 Add a Vitest case that, with the dialog open on that combo cell, briefly sets article tree selection to `[]` then restores the same single article and asserts `locked_addition_ids` are unchanged — verify the new case fails under the current wipe behaviour
- [x] 1.3 Keep or extend existing cases that clear locked ids when a second article or any voucher is selected, and when the single base article changes — verify those still pass after the fix

## 2. Dialog watcher / clear behaviour

- [x] 2.1 Split “clear options / cancel in-flight fetch” from “clear selected locked ids” in `EventConfigLayoutsSection.vue` so transient ineligible selection does not zero seeded ids — verify task 1.2 passes
- [x] 2.2 Clear selected locked ids only on durable eligibility loss (second article, any voucher, or different single base article), matching design.md — verify task 1.3 still passes
- [x] 2.3 After Zusatz options load for the current base article, intersect `locked_addition_ids` with available option ids so orphans do not linger — verify with a unit assertion or existing open+load path

## 3. Verification

- [x] 3.1 Run the EventConfigLayoutsSection Vitest file (and any related payload util tests if touched) and confirm all pass
- [x] 3.2 Run `./scripts/lint.sh --staged` (or full `./scripts/lint.sh` if preferred) on touched frontend files before commit and confirm clean
