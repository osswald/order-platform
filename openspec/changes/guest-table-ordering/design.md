## Context

See proposal.md for motivation. Today orders are created on the Pi (`waiter` / `cash_register`); cloud receives them via edge push. Tables are integer `table_number` values with no floor-plan entity. Staff devices use venue Wi‑Fi; guests must not. Event config already has sectioned admin UI (stations, layouts, …) and `edge_credential.last_seen_at` updates on edge auth. Sync today pulls catalogue/bundle and pushes outbox; there is no cloud→Pi order ingress for guests.

## Goals / Non-Goals

**Goals:**

- Cloud-hosted guest runtime (`order.vendiqo.ch`) with prepaid rounds (SumUp Payment Widget) that only enter Pi after verified payment.
- Admin-configurable guest menu (categories from station articles), thresholds, and printable table QRs.
- Feature-gated Pi poller that pulls/acks paid guest orders and reuses local kitchen/stock/print paths.
- Keep waiter table service and settlement semantics unchanged.

**Non-Goals:**

- SumUp Hosted Checkout (redirect) for guest pay — Payment Widget is the chosen collection UI.
- TWINT (or other APMs) on the guest pay surface.
- Changing staff POS payments (`sumup`, `sumup_connected` Solo readers, cash, event TWINT QR).
- Shared multi-guest carts or seat-level ordering.
- Guest access to venue Wi‑Fi or Pi LAN APIs.
- Replacing staff `app_layouts` with the guest menu.
- Guest void/refund after payment (staff exception handling only).
- Auto-refund orchestration when Pi rejects an already-paid order (document risk; follow-up).

## Decisions

### D1 — Host guest UI on `order.vendiqo.ch`

Separate origin from `admin.vendiqo.ch` for trust, cookie isolation, smaller bundle, independent deploy, and clear CORS allowlist entry. QR deep links encode `https://order.vendiqo.ch/...`. Admin remains the configure/print surface.

**Alternatives:** Path under admin (rejected: mixes auth worlds); path under www marketing (rejected: wrong product).

### D2 — Pay in cloud, then Pi pull (not push)

Guest payment completes against cloud; order enters a durable **paid inbox**. Pi runs a **separate poller** (not the catalogue sync loop) only when self-order is active for a paired event, pulls pending paid orders, applies locally, acks. Offline Pi → inbox queues; guest soft-gate (D5) limits new checkouts.

**Alternatives:** Cloud push to Pi (needs new reachability); guest posts to Pi on LAN (violates Wi‑Fi rule).

### D3 — `order_source` / settlement boundary

Guest-applied orders are born **paid** on the Pi with table routing for kitchen/print. They MUST NOT enter waiter open-tab settle / split / Sammelrechnung flows. Waiter orders on the same table continue under existing `payment_mode`.

### D4 — Guest menu model vs staff layouts

When self-order is enabled, event config shows a **Guest menu** section: ordered categories; each category holds articles chosen from the event’s station assortment (preserves station→kitchen routing). Staff layouts unchanged. Guest catalog API serves this structure, applying stock visibility rules from cloud stock snapshot.

### D5 — Pi liveness gate for guest checkout

Cloud compares `now - edge_credential.last_seen_at` (server appliance for the event) to configurable `pi_offline_after_minutes` (default 10). If exceeded: guest UI shows a **soft message** and blocks starting/completing payment; browsing may remain. Edge guest-order poll traffic refreshes `last_seen_at`.

### D6 — Stock visibility and deduction split

- **Visibility (cloud guest menu):** monitored articles with `in_stock < hide_below_stock` (default 15, configurable) are hidden; unmonitored always shown. Uses cloud stock as updated by existing edge order stock deduct on Pi→cloud sync.
- **Deduction:** only when Pi applies a pulled guest order (existing local stock path). Cloud MUST NOT deduct guest stock at payment time.

### D7 — Identity and QR

QR carries event public id (or opaque event slug), `table_number`, and a rotatable table/event token. Each checkout creates a new guest order (no join-table session). QR artwork places the human-readable table number in the center; print/PDF from Guest menu tab for a table range.

### D8 — SumUp Payment Widget (online checkout)

Guest pay uses SumUp **online** checkouts + **Payment Widget**, not Solo reader checkouts and not Hosted Checkout.

Flow:

1. Cloud creates a SumUp checkout (`POST /v0.1/checkouts`) for the event organisation’s SumUp merchant (amount, currency, reference = guest order id).
2. Guest frontend mounts the Payment Widget with `checkoutId` on `order.vendiqo.ch` (HTTPS; CSP allows SumUp gateway script).
3. Widget handles card entry / 3DS; client `onResponse` is UX-only.
4. Cloud marks the guest order **paid** only after verified checkout status (retrieve and/or webhook), then moves it to the Pi pull inbox.
5. TWINT and other APMs are **not** offered for guest orders (configure/hide widget APM options accordingly; do not promise TWINT on guest UI).

**Alternatives considered:** Hosted Checkout (rejected for this change — leaves origin, weaker stay-at-table continuity); Solo reader (rejected — staff device, not guest phone); TWINT on guest (explicitly out of scope).

### D9 — Guest order lifecycle

```
draft → awaiting_payment → paid → pending_pull → applied_on_pi
                         ↘ cancelled | expired | failed
```

Guest cancel only while not `paid`. Idempotent Pi apply/ack by stable `guest_order_id`.

## Risks / Trade-offs

- **[Risk] Paid while Pi dark (under threshold)** → Orders sit in inbox until pull; UI confirms “sending to venue.” Soft-gate at N minutes stops new pays.
- **[Risk] Cloud stock lag vs Pi truth** → Hide-below buffer reduces phone oversell; residual race possible. Mitigation later: reserve or refund-on-reject.
- **[Risk] Pi reject after pay (stock/event closed)** → No auto-refund in scope; surface ops alert / manual handling; follow-up for provider refunds.
- **[Risk] Tokenized QR leaks** → Rotatable tokens; bind to event; rate-limit public APIs.
- **[Trade-off] Separate poller vs sync loop** → More moving parts; faster/lighter guest delivery without coupling to fat bundle pulls.
- **[Trade-off] New frontend package** → Deploy/DNS cost; cleaner than shipping guest UI inside admin.
- **[Risk] Org merchant lacks online checkout** → Guest pay fails until SumUp online payments are enabled for that merchant; surface a clear admin/guest error. Solo-only orgs are not enough.
- **[Risk] Widget CSP / 3DS on mobile browsers** → Follow SumUp widget HTTPS/CSP guidance; test iOS/Android Safari/Chrome early.

## Migration Plan

1. Ship cloud models/APIs + admin Guest menu tab (feature off by default).
2. Deploy `order.vendiqo.ch` guest app with SumUp Payment Widget wired to online checkout create + webhook verify.
3. Ship Pi poller behind feature detection from bundle/event flag.
4. Enable per event (requires org SumUp online checkout capability); print QRs; validate pay → pull → kitchen.
5. Rollback: disable event flag (poller idle, guest soft-closed); inbox drains or remains unpaid-path only.

## Open Questions

- Default guest-order poll interval (suggest 5–15s; tune in implementation).
- Exact public URL path shape (`/e/{id}/t/{n}` vs signed opaque link).
- Whether waiter UI shows read-only “recent guest orders on this table” in MVP or later.
- Exact SumUp widget config flags to suppress APMs/TWINT for guest (confirm against current SumUp widget docs at implement time).
