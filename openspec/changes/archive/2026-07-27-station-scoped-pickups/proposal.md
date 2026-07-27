## Why

Cash-register orders allocate one pickup code for the whole order, but print a separate customer Abholbeleg per production station. Guests holding several slips with the same code cannot collect Grill when it is ready while Bar is still cooking. Station-scoped codes with independent ready/picked-up state fix that.

## What Changes

- Allocate **one sequential pickup number per production station** that has article lines on a cash-register order (same register prefix; burn N numbers from the event counter). Single-station orders stay one code.
- Print each customer Abholbeleg and kitchen ticket with **that station’s** pickup code.
- Track **per-station pickup status** (`pending` / `ready` / `picked_up`) so one station can show Bereit while another stays In Arbeit; mark picked-up **one code at a time**.
- Pickup screen lists **one tile per station pickup** (not one per order). Ready TTL expires per code.
- Register customer display and pay success show **all** codes for the order.
- Open-orders hub stays **one row per order**, showing all codes (e.g. `A1, A2`).
- Create-order API exposes `pickup_codes` (keep `pickup_code` as the first code for compatibility).
- Partial settlement continues to leave pickups on the original open order (all station codes).

## Capabilities

### New Capabilities
- `station-scoped-pickups`: Per-station pickup allocation, status lifecycle, pickup screen/API, register display of multiple codes, and kitchen ticket code binding for cash-register orders

### Modified Capabilities
- `register-order-settlement`: Open/paid create and open-orders listing MUST reflect multi-code allocation (still one order row; codes stay on the original order after partial settle)

## Impact

- **Pi backend**: order create allocation; new station-pickup persistence; pickup list/picked-up/TTL; kitchen ticket print → station ready; order payload / cloud sync shape; OpenAPI schemas
- **Pi frontend**: PickupScreen (per-code tiles); RegisterDisplay / pay success / hub open-orders label; kitchen ticket header already shows `pickup_code` from ticket payload
- **Tests**: multi-station create, independent ready/picked-up, single-station unchanged, open-orders label, display payload
- **Non-goals**: waiter/table orders; changing cash-register prefix config; voucher-only orders (still no pickup slips); station-owned prefixes; cloud admin UI
