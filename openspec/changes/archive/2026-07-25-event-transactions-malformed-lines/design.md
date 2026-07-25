## Context

Edge orders store their payload as flexible JSON. The transaction-history read path later assumes each line satisfies the Pi contract: `_line_cents_from_payload()` sends every dictionary line to `_line_for_pricing()`, which directly indexes `line["article_id"]`. During the Stripe simulation, one line without that key caused `GET /events/4/transactions` to fail for the whole page.

The display formatter already skips lines whose `article_id` is absent, but total calculation does not. Other malformed numeric fields can raise `TypeError` or `ValueError` through the same pricing helpers, creating similar page-wide failures.

## Goals / Non-Goals

**Goals:**

- Return a usable transaction page when one or more persisted lines are malformed.
- Apply one consistent definition of a renderable line to count, details, and line-total calculation.
- Preserve every valid line and all order-level/payment information.
- Add regression coverage at the HTTP endpoint.

**Non-Goals:**

- Tightening the flexible `POST /edge/v1/orders` payload contract.
- Repairing or deleting historical payload JSON.
- Inventing an article id or price for a malformed line.
- Changing the response schema or frontend.

## Decisions

### 1. Sanitize lines at the transaction read boundary

Add a small transaction-specific helper that accepts dictionary lines only when the existing pricing conversion and total calculation can process them. It SHALL reject a line when required identifiers are missing or when identifier, quantity, unit price, or addition values cannot be converted as expected.

Use the resulting valid-line list for:

- `line_count`
- `format_payload_lines`
- `line_cents`

This keeps all three fields internally consistent.

**Alternative:** Relax `_line_for_pricing()` globally. Rejected because it is a shared sales helper whose other callers may rely on validated data and should not silently change semantics.

### 2. Skip malformed lines instead of estimating them

A malformed line contributes neither details nor value to `line_cents`. Payment entries remain visible and continue contributing to `paid_cents` and `payment_methods`.

**Why:** The API cannot reliably infer an article or authoritative price. Returning a lower line total alongside the unchanged paid amount exposes the data discrepancy without fabricating sales data.

### 3. Isolate failures per line

Validation SHALL catch only expected payload conversion failures (`KeyError`, `TypeError`, `ValueError`) per line. Unexpected programming errors must still surface rather than being hidden by a broad exception handler.

### 4. Test through the public endpoint

Seed persisted orders containing:

- one line missing `article_id`
- one invalid line mixed with a valid line
- a malformed numeric identifier

Assert HTTP 200, preservation of payment information, and totals/details derived from valid lines only.

## Risks / Trade-offs

- [Risk] Skipping a malformed line understates `line_cents` → Mitigation: preserve `paid_cents`; do not invent values; malformed source data remains available in the stored payload for diagnosis.
- [Risk] Silent degradation can hide producer bugs → Mitigation: emit a warning with event/order identity and skipped-line count, without logging full customer/order payloads.
- [Trade-off] Ingestion remains permissive → Accepted for backward compatibility; stronger schema validation can be proposed separately with Pi version coordination.

## Migration Plan

1. Add failing endpoint regression tests.
2. Add defensive line filtering and warning logging.
3. Deploy without data migration or OpenAPI regeneration.
4. Roll back the code if needed; no persisted state changes are introduced.

## Open Questions

None. The safe default is to preserve page availability and skip only lines that cannot be priced deterministically.
