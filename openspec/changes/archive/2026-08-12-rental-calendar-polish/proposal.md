## Why

Several rental calendar and packing UX improvements shipped after the OpenSpec-backed rental work (v2.8.1–v2.8.6) without delta specs. Living specs still describe older calendar chrome (per-day chips, Flotte naming, no tooltips/IPs) and miss catalog quantity override and packing PDF label/IP behaviour.

## What Changes

- **Retroactive only** — behaviour already shipped; this change captures requirements into OpenSpec and syncs living specs. No further product code.
- Document month spanning bars, year overlap lanes, bar tooltips, appliance type chips, Geräte (ex-Flotte) naming, printer IP exposure on calendar/fleet/edit, delete toast without hiding the calendar.
- Document catalog Zubehör quantity override on add.
- Document packing PDF printer IPs, localized appliance type labels, and stable type sort order.
- Document Verleiher-Einstellungen nav for platform admins with an active hire company.

## Capabilities

### New Capabilities

- `verleiher-settings-nav`: Platform admins with an active Verleiher see the same Verleiher settings nav entry as tenant admins.

### Modified Capabilities

- `rental-calendar`: Calendar presentation (spanning bars, year lanes, tooltips, type chips, Geräte view, IPs), delete keeps calendar visible.
- `rental-zubehoer`: Adding from catalog may override quantity (prefilled from default).
- `rental-packing-pdf`: Geräte rows show IP when present, localized type labels, and ordered type groups.

## Impact

- OpenSpec living specs and archive only.
- No API or application code changes in this change (already on main).
