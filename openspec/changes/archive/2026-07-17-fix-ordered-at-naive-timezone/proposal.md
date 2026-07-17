# Proposal: fix-ordered-at-naive-timezone

## Why

`parse_ordered_at` in the cloud backend treats naive `datetime` objects as UTC, but ISO strings without a UTC offset (e.g. `"2026-06-25T10:30:00"` from Pi order payloads) are returned as naive datetimes. These naive values flow into event statistics timeframe comparisons (raising `TypeError` against timezone-aware bounds) and into the `edge_order_items.ordered_at` DB backfill (storing inconsistent timestamps).

## What Changes

- `parse_ordered_at` normalizes successfully parsed offset-less ISO strings to UTC, matching the existing behavior for naive `datetime` objects.
- Regression tests cover offset-less strings, `Z`-suffixed strings, and the existing offset-bearing case.

## Capabilities

### New Capabilities

- `event-stats-timestamp-parsing`: parsing of `ordered_at` values (datetimes and ISO strings) for event statistics and order-item backfills; all valid inputs yield timezone-aware (UTC) datetimes.

### Modified Capabilities

<!-- none — this is the first spec for this capability -->

## Impact

- `cloud/backend/app/event_stats.py`: ~2 lines in `parse_ordered_at`
- `cloud/backend/tests/test_event_stats.py`: 2-3 new test cases
- Downstream beneficiaries (no code change needed): `effective_ordered_at`, `resolve_sync_ordered_at`, `_backfill_edge_order_items_ordered_at_from_payload` in `cloud/backend/app/database.py`
