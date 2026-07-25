## Why

`GET /events/{event_id}/transactions` returns HTTP 500 when any stored order line lacks `article_id`, because transaction totals call `_line_for_pricing()` with an assumed key. Edge order payloads are persisted as flexible JSON, so one malformed or legacy line must not make the entire event transaction history unavailable.

## What Changes

- Make event transaction rendering tolerate malformed order lines, including missing or non-numeric `article_id`.
- Skip invalid lines consistently from line details, line count, and computed line totals while preserving valid lines and payment information from the same order.
- Add regression tests proving a malformed line cannot crash the endpoint or hide other transactions.
- Keep the edge order submission contract unchanged; stricter ingestion validation is out of scope to avoid breaking older Pi clients.

## Capabilities

### New Capabilities

- `event-transaction-resilience`: Defines how the cloud transaction-history API degrades safely when persisted order payloads contain malformed lines.

### Modified Capabilities

- None.

## Impact

- **Cloud backend:** defensive parsing in `event_transactions.py` and/or shared `event_sales.py` line helpers.
- **Tests:** event transaction API coverage for missing/invalid article identifiers and mixed valid/invalid lines.
- **API compatibility:** no route or response-schema changes; valid transaction output remains unchanged.
- **Data:** no migration or rewriting of historical order payloads.
