# Design: fix-ordered-at-naive-timezone

## Context

`parse_ordered_at` (`cloud/backend/app/event_stats.py:33`) already normalizes naive `datetime` objects to UTC but returns naive datetimes when parsing offset-less ISO strings. Its results are consumed by `effective_ordered_at`, `resolve_sync_ordered_at`, and the DB backfill `_backfill_edge_order_items_ordered_at_from_payload` (`cloud/backend/app/database.py:463`), all of which expect timezone-aware values.

## Goals / Non-Goals

**Goals:**

- All successful `parse_ordered_at` results are timezone-aware (UTC assumed when absent).
- Regression tests pin the behavior for all input shapes.

**Non-Goals:**

- No change to how Pi devices serialize `ordered_at` (out of scope; cloud must stay tolerant regardless).
- No change to invalid-input handling (still returns `None`).
- No DB migration; the existing backfill picks up correct values for future runs.

## Decisions

### Decision 1: Normalize at the parse boundary

Apply `replace(tzinfo=UTC)` to the `fromisoformat` result when it is naive, inside `parse_ordered_at` itself, rather than at each call site. This mirrors the existing datetime-object branch (line 37) and keeps all callers correct with a single change.

### Decision 2: Assume UTC for offset-less values

Pi devices record timestamps in UTC internally, and the datetime-object branch already assumes UTC for naive values. Assuming UTC for offset-less strings keeps both branches consistent.
