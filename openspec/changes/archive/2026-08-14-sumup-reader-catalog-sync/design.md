## Context

See proposal.md — Why. Cloud already lists SumUp readers via `GET /v0.1/merchants/{merchant_code}/readers` but only copies `status` onto existing `sumup_readers` rows. Connect stores merchant + API key and never reads that catalog. SumUp’s Reader object includes `id`, `name`, `status`, and `device.identifier` / `device.model`. Live battery/online data is a separate `GET …/readers/{reader_id}/status` (Solo firmware 3.3.39.0+). There is no cloud job runner; Pi edge bundle already exposes local rows only.

## Goals / Non-Goals

**Goals:**

- One catalog-sync function used on connect, same-merchant key update, and reader list.
- Prune only after a successful well-formed SumUp list (never on transport/parse failure).
- Lazy telemetry endpoint + SumUp-Geräte tooltip; catalog list stays cheap.
- Clear cash-register `sumup_reader_id` when a reader is pruned.

**Non-Goals:**

- Background scheduler / cron.
- Calling SumUp on every Pi edge-bundle poll.
- Auto-calling SumUp Create Reader (pairing code flow stays for new hardware).
- Overwriting Vendiqo labels from SumUp `name` after first import.
- Showing telemetry on Pi POS pickers in this change.

## Decisions

1. **Sync triggers = connect + list, no worker**  
   Reuse FastAPI request paths. List already hits SumUp; extend it to upsert/prune. Connect and same-merchant API-key update call the same helper after credentials are stored.  
   **Alternatives considered:** Lifespan loop over all connected orgs — new infra, extra SumUp traffic when nobody is in admin. Rejected.

2. **Prune when `reader_id` missing from a well-formed list**  
   Treat `{ "items": [ ... ] }` as authoritative. Empty `items` deletes all local rows for that org. If `items` is missing or not a list, or the HTTP call fails, skip prune (keep last snapshot).  
   **Alternatives considered:** Keep stale rows (user rejected — unregistered devices cannot pay). Soft-delete / `missing` status — extra UI for hardware that cannot check out.

3. **Label policy**  
   Insert: `name` if non-empty, else `device.identifier`, else `"Solo"`. Update: never replace local `label`. Rename still PATCHes SumUp `name`.  
   **Alternatives considered:** Always mirror SumUp `name` — would undo admin renames.

4. **Persist serial/model on `sumup_readers`**  
   Nullable `device_identifier` and `device_model` columns, returned on list so the tooltip has identity without a second call. Schema patch via existing `database.py` helpers + Alembic if the project requires both.  
   **Alternatives considered:** Fetch identity only with telemetry — tooltip would be empty when `/status` fails.

5. **Prune clears cash-register defaults**  
   `UPDATE event_cash_registers SET sumup_reader_id = NULL` for that `reader_id` on events of the organisation. Waiter POS bindings live in Pi session/localStorage; next bundle simply omits the reader.  
   **Alternatives considered:** Block prune while a register references the reader — leaves a useless device in pickers.

6. **Telemetry is on-demand**  
   `GET /sumup/organisations/{org_id}/readers/{reader_id}/telemetry` maps SumUp `/status` (`data.status`, `battery_level`, `connection_type`, `firmware_version`, `last_activity`, `state`) plus stored serial/model. Frontend `v-tooltip` on the label fetches once per hover (short in-memory cache OK). List/status APIs do not embed live telemetry.  
   **Alternatives considered:** N status calls on every list — slow and firmware-gated.

7. **Connect failure isolation**  
   Catalog sync after successful credential persist is best-effort: SumUp list errors must not roll back connect. Same as today’s “list still works when SumUp is down.”

## Risks / Trade-offs

- **[Risk] Malformed list parsed as empty `items` wipes all readers** → Mitigation: prune only when `items` is a present list; tests for missing/`null` `items`.
- **[Risk] Live vs sandbox merchant** → Mitigation: unchanged merchant picker; import is for the connected `merchant_code` only.
- **[Risk] `/status` 404 on old firmware** → Mitigation: tooltip degrades; catalog unaffected.
- **[Risk] Prune during an in-flight checkout** → Mitigation: edge checkout already 404s if the local row is gone; rare if SumUp deleted the reader.
- **[Trade-off] POS does not see a dashboard-paired Solo until someone opens SumUp-Geräte (or reconnects)** → Accepted vs a scheduler.

## Migration Plan

1. Add columns + OpenAPI; deploy backend sync + telemetry (backward compatible: empty catalog still lists local-only until first successful SumUp list).
2. Ship SumUp-Geräte tooltip.
3. First list/connect after deploy imports me.sumup.com readers and may prune stale local ids.
4. Rollback: revert deploy; leftover serial columns are harmless; re-pair remains available.

## Open Questions

- None blocking; tooltip copy/i18n can be finalized during apply.
