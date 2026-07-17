# Tasks: fix-ordered-at-naive-timezone

## 1. Tests first (per repo convention)

- [x] 1.1 Add tests to `cloud/backend/tests/test_event_stats.py` covering: offset-less ISO string returns UTC-aware datetime, `Z`-suffixed string, naive `datetime` object, unparseable string returns `None`
- [x] 1.2 Run the new tests and confirm the offset-less string case fails (red)

## 2. Fix

- [x] 2.1 Normalize naive `fromisoformat` results to UTC in `parse_ordered_at` (`cloud/backend/app/event_stats.py`)

## 3. Verify

- [x] 3.1 Run the full cloud backend test suite
- [x] 3.2 Run `./scripts/lint.sh` (or `--staged` before commit)
