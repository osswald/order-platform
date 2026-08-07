## 1. Event settings and guest menu data model

- [ ] 1.1 Add failing cloud backend tests for event guest self-order flag, hide-below stock threshold (default 15), Pi offline minutes (default 10), and guest menu category/article persistence rules (articles must be on event stations)
- [ ] 1.2 Implement Event guest self-order settings + guest menu category/article models, schema patches/migrations, and admin read/write APIs
- [ ] 1.3 Include guest self-order settings (and any Pi-needed flags) in the edge bundle/event configuration payload
- [ ] 1.4 Export OpenAPI and regenerate cloud frontend API types

## 2. Admin Guest menu configuration UI

- [ ] 2.1 Add failing cloud frontend tests for Guest menu section visibility when the feature is enabled
- [ ] 2.2 Add event toggle for guest self-order and threshold fields (stock hide-below, Pi offline minutes)
- [ ] 2.3 Implement Guest menu tab/section: create/reorder categories; add/remove articles from station assortment
- [ ] 2.4 Keep staff layouts section behavior unchanged when guest menu is configured

## 3. Table QR generation and print

- [ ] 3.1 Add failing tests for QR payload (order host + event + table + token) and centered table-number rendering constraints
- [ ] 3.2 Implement QR token minting/rotation for event tables and render QR with table number in the center
- [ ] 3.3 Add Guest menu tab print/PDF (or print-friendly page) for a table number range
- [ ] 3.4 Document DNS/`ALLOWED_ORIGINS` requirement for `order.vendiqo.ch` (or env equivalent)

## 4. Cloud guest order runtime and inbox

- [ ] 4.1 Add failing tests for guest catalog visibility (unmonitored always shown; monitored hidden when `in_stock` < threshold) and Pi soft-gate using edge last-seen vs configured minutes
- [ ] 4.2 Implement public guest APIs: resolve QR/token → event/table; serve guest menu catalog with stock rules; create draft order; cancel only before pay
- [ ] 4.3 Implement payment-session boundary (provider-agnostic): awaiting_payment → paid | failed | cancelled; on paid, place order in Pi pull inbox without cloud stock deduction
- [ ] 4.4 Implement edge endpoints for Pi to pull pending paid guest orders and ack apply (idempotent by guest order id); ensure auth refreshes last-seen
- [ ] 4.5 Rate-limit and authz-scope public guest endpoints; reject checkout when Pi soft-gate is active

## 5. Guest frontend (`order.vendiqo.ch`)

- [ ] 5.1 Scaffold guest frontend package (Vue 3 / Vite / Node 24) separate from admin, with deploy/host wiring notes for the order subdomain
- [ ] 5.2 Implement QR landing → menu browse by guest categories → cart → pay (stub provider) → stay-at-table confirmation with table number
- [ ] 5.3 Implement soft unavailable message and blocked pay when API reports Pi offline beyond threshold; allow browse
- [ ] 5.4 Add guest frontend tests for catalog filtering display, cancel-before-pay, and offline soft-gate UX

## 6. Pi guest-order pull and local apply

- [ ] 6.1 Add failing Pi backend tests for: poller idle when feature off; pull/apply/ack when on; born-paid local order with table routing; stock deduct on apply; idempotent duplicate pull; exclusion from open-tab settlement
- [ ] 6.2 Implement dedicated guest-order poller (separate from catalogue sync), enabled only when a paired event has guest self-order active
- [ ] 6.3 Apply pulled orders into local paid guest orders; reuse kitchen/print routing; deduct stock via existing local path; ack cloud
- [ ] 6.4 Ensure waiter create/settle paths remain unchanged and do not settle prepaid guest orders

## 7. Verification and docs

- [ ] 7.1 Run cloud backend, Pi backend, cloud frontend, and guest frontend tests for touched areas
- [ ] 7.2 Run `./scripts/lint.sh` on staged/changed areas
- [ ] 7.3 Update privacy/hosting notes if required for the new guest host; note payment-rail follow-up in change docs
