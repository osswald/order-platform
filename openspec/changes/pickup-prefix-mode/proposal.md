## Why

Pickup codes are `{letter}{number}` (letter 1–3 `A–Z`). Today the letter always comes from the cash register, which answers “which till sold this.” For multi-window events the letter should answer “which station to collect from” (e.g. Grill `G17`, Bar `B3`). Station-scoped pickups already allocate one code per production station; only the letter source and number counter need an event-level mode.

## What Changes

- Add an event-level `pickup_prefix_mode`: `register` (default, current behaviour) or `station`.
- In **station** mode:
  - Each production station has a required `pickup_code_prefix` (1–3 `A–Z`), unique within the event.
  - Cash-register prefix fields are hidden and unused for allocation.
  - Pickup numbers use a **per-station** counter (not the shared event counter).
  - Every article that can be sold on the event MUST belong to a station (no null-station pickup groups).
- In **register** mode: keep today’s register prefixes + single event-wide counter; hide station prefix fields.
- Changing `pickup_prefix_mode` is **forbidden** once the event leaves `config` (locked in `test` / `prod` / `archive`).
- On **test → prod**, all pickup-code counters for the event SHALL reset (event-wide and per-station) so production numbering starts fresh (already part of Pi operational purge; keep covering per-station rows).
- Event copy copies the mode and the prefixes used by that mode (register prefixes and/or station prefixes).
- Edge bundle carries the mode and station prefixes so Pi allocation can follow it.
- Printer-rule `pickup_prefix` (routing) is unchanged.

## Capabilities

### New Capabilities

- `pickup-prefix-mode`: Event-level register vs station letter source, config UI visibility, validation (unique station prefixes, articles on stations), mode lock after `config`, per-station counters, test→prod counter reset, and event-copy behaviour.

### Modified Capabilities

- `station-scoped-pickups`: Cash-register order allocation SHALL take the letter from the active mode (register prefix vs station prefix) and SHALL advance the matching counter (event-wide vs per-station).

## Impact

- **Cloud backend**: `Event` mode field; `EventStation.pickup_code_prefix`; config validation; event copy; edge bundle payload; OpenAPI.
- **Cloud frontend**: Event config switch; show/hide register vs station prefix fields; i18n; regenerate API types.
- **Pi backend**: Read mode from bundle; allocate with station prefix + per-station `EventPickupCounter`; reject/impossible null-station article lines when mode is station.
- **Pi frontend**: No UX change expected if codes remain opaque strings (customer display / pickup screen already show allocated codes).
- **Tests**: Cloud validation/copy/bundle; Pi allocation and station-scoped pickup suites.
