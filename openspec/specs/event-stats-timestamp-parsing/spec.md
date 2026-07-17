# event-stats-timestamp-parsing Specification

## Purpose
TBD - created by archiving change fix-ordered-at-naive-timezone. Update Purpose after archive.
## Requirements
### Requirement: Ordered-at parsing yields timezone-aware UTC datetimes

The cloud backend SHALL return a timezone-aware datetime from `parse_ordered_at` for every successfully parsed input. Inputs without timezone information SHALL be interpreted as UTC.

#### Scenario: Naive datetime object

- **WHEN** `parse_ordered_at` receives a naive `datetime` object
- **THEN** it returns the same wall-clock time with `tzinfo=UTC`

#### Scenario: ISO string with explicit offset

- **WHEN** `parse_ordered_at` receives `"2026-06-25T10:30:00+00:00"`
- **THEN** it returns the corresponding timezone-aware datetime unchanged

#### Scenario: ISO string with Z suffix

- **WHEN** `parse_ordered_at` receives `"2026-06-25T10:30:00Z"`
- **THEN** it returns the corresponding datetime with `tzinfo=UTC`

#### Scenario: ISO string without offset

- **WHEN** `parse_ordered_at` receives `"2026-06-25T10:30:00"` (no offset)
- **THEN** it returns `2026-06-25 10:30:00` with `tzinfo=UTC`, not a naive datetime

### Requirement: Invalid or empty inputs return None

`parse_ordered_at` SHALL return `None` for `None`, empty or whitespace-only strings, and strings that are not valid ISO 8601 datetimes.

#### Scenario: Unparseable string

- **WHEN** `parse_ordered_at` receives `"not-a-date"`
- **THEN** it returns `None`

