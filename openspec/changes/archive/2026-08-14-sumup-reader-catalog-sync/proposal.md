## Why

Connecting a SumUp merchant on SumUp-Geräte stores the API key but does not import Solo readers already paired in me.sumup.com. Admins see an empty list and must re-pair hardware that SumUp already knows. A reader that later disappears from SumUp stays in Vendiqo even though it can no longer take payments.

## What Changes

- On **connect** (and same-merchant API-key update), import the merchant’s Cloud API reader catalog into local `sumup_readers`.
- On every **reader list**, upsert that catalog: insert new remote ids, refresh pairing status, drop local rows whose `reader_id` is no longer on SumUp. No background scheduler.
- Use SumUp `name` as the Vendiqo label on import; keep the local label on later syncs (rename remains the source of truth).
- Persist device serial/model from the catalog; expose live Solo telemetry (online, battery, connection, firmware) as a **tooltip** on paired readers, fetched lazily on hover.
- When a pruned reader was assigned as a cash-register default, clear that binding. POS pickers follow the local table / edge bundle as today.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `sumup-solo-readers`: Catalog sync on list (import + prune + status); store device identity; telemetry tooltip on SumUp-Geräte.
- `sumup-cloud-connect`: Connect (and same-merchant key update) imports the merchant reader list so SumUp-Geräte is populated without a second pairing step.

## Impact

- Cloud backend: expand reader list sync beyond status-only; call the same sync from connect/update; new telemetry endpoint wrapping SumUp `GET …/readers/{id}/status`; optional columns for serial/model; OpenAPI export + frontend types.
- Cloud frontend: SumUp-Geräte reader table tooltip; lazy telemetry fetch.
- Pi / edge checkout: unchanged call shape; pruned readers simply drop out of the edge bundle.
- No new job runner or SumUp calls on Pi poll.
