## Context

The public marketing site lives in `website/` as a Vite multi-page static app (nginx in prod via `cloud/docker-compose.prod.yml` + Caddy). Today it has only Start (`/`) and Datenschutz (`/datenschutz/`), German hardcoded copy, no product screenshots, and no inquiry path. Vendiqo operates as a single Verleiher: organisations rent the system for events and reuse org setup across rentals. Product surfaces to showcase: Cloud admin (org/event setup), Pi on-site, Android waiter. Play Store tablet captures already exist under `android/play-store-screenshots/`; Cloud/Pi marketing shots do not.

Cloud backend has rate limiting (`slowapi`) and CORS via `ALLOWED_ORIGINS`, but no outbound email/SMTP utilities yet.

## Goals / Non-Goals

**Goals:**

- Multi-page German marketing IA: Start, Ablauf, Funktionen, Kontakt, Datenschutz
- Narrative on Ablauf starts with organisation + event setup, then on-site flow, then reuse for the next rental
- Screenshot + short text bands on Ablauf and Funktionen
- Mietanfrage form posts to a public API that sends email only (no DB persistence of leads)
- Primary CTA = Mietanfrage; Admin remains secondary for Bestandskunden
- Datenschutz updated for inquiry processing

**Non-Goals:**

- English (or any second locale) on the marketing site
- Multi-Verleiher / marketplace messaging
- Storing inquiries in PostgreSQL or an admin “Leads” UI
- Pricing page, blog, live embedded demo, or chatbot
- Redesigning the authenticated cloud/Pi apps
- Automated screenshot CI pipeline in v1 (manual or one-off capture is enough)

## Decisions

### 1. Information architecture — separate pages

**Decision:** Keep the existing MPA pattern (Vite `rollupOptions.input` + `page/index.html` folders). Add:

| Path | Role |
|------|------|
| `/` | Brand hero, short pitch, teasers linking to Ablauf / Funktionen / Kontakt |
| `/ablauf/` | Ordered journey with screenshots (Org → Event → Bestellen → Küche → Zahlen → Wiederverwenden) |
| `/funktionen/` | Scannable capability bands (Cloud, Pi, Android, Zahlungen, Belege, …) each with screenshot + headline + one sentence |
| `/kontakt/` | Mietanfrage form |
| `/datenschutz/` | Existing privacy page (content update) |

Shared header/footer via existing `layout.js`. Nav: Ablauf, Funktionen, Mietanfrage (emphasized), Admin (external), Datenschutz in footer.

**Alternatives considered:**

- Single long home — rejected; user asked for several pages
- Merge Ablauf + Funktionen — rejected; narrative vs capability scan serve different jobs

### 2. Language — German only

**Decision:** All marketing UI strings and meta tags remain German (`lang="de"`). No i18n framework on `website/` for this change.

### 3. Email-only inquiry delivery via cloud public API

**Decision:** Add an unauthenticated public endpoint on the cloud backend, e.g. `POST /public/rental-inquiry`, that validates the payload and sends one email to a configured inbox (`RENTAL_INQUIRY_TO`). Website form submits via `fetch` to `api.vendiqo.ch` (env-configurable API base for local/dev).

Implementation sketch:

- Pydantic request model: name, organisation, email, phone (optional), event_dates / timeframe, message; honeypot field that must be empty
- Response: `202`/`204` on accept; generic error bodies (no SMTP internals leaked)
- Rate limit with existing `slowapi` limiter (strict per-IP)
- Outbound mail via SMTP settings from env (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `RENTAL_INQUIRY_TO`); use stdlib `smtplib` or a thin helper — no lead table
- If SMTP is not configured: endpoint returns `503` in production; in development may log the message body instead of sending (documented)
- CORS: ensure prod `ALLOWED_ORIGINS` includes `https://vendiqo.ch` and `https://www.vendiqo.ch`
- CSRF: public JSON POST from marketing origin; either exempt this route from cookie CSRF (no session cookies involved) or use a double-submit/origin check already aligned with `allowed_origins`

**Alternatives considered:**

- Third-party form→email (Formspree, etc.) — faster, but adds a processor and Datenschutz complexity; rejected for v1 preference to keep data with Vendiqo
- Mailto: links — poor UX and no structured fields; rejected
- Persist leads in DB — explicitly out of scope

### 4. Form fields

**Decision:** Collect:

- Name (required)
- Organisation / Verein / Betrieb (required)
- E-Mail (required)
- Telefon (optional)
- Zeitraum / Event-Datum(e) (required)
- Nachricht (required)
- Honeypot (hidden, must be empty)
- Short notice + link to Datenschutz near submit

Success: inline confirmation on `/kontakt/` (“Anfrage gesendet”). No thank-you microsite required.

### 5. Screenshots and sample data

**Decision:**

- **Android / on-site bands:** reuse or lightly crop existing Play Store captures (`android/play-store-screenshots/`), copied into `website/public/images/` (do not deep-link the Android folder from the static site build)
- **Cloud setup bands (Organisation, Event, ggf. Geräteausleihen):** capture from admin with a prepared sample organisation (pretty names, CHF, plausible catalog). Store PNGs/WebPs under `website/public/images/`
- Each band: one image + German headline + one short supporting sentence
- Prefer WebP with PNG fallback if build tooling stays simple; PNG-only is acceptable for v1
- Alt text in German describing the UI, not marketing fluff

**Alternatives considered:** Waiting for a full screenshot CI pipeline — defer; ship curated static assets first.

### 6. Visual approach

**Decision:** Evolve the existing marketing CSS rather than adopting Vuetify or the cloud admin shell. Keep a light, calm Verleih-marketing look consistent with current slate/blue tokens, but allow modest atmosphere (subtle gradient/pattern) and clearer hierarchy for multi-section pages. Feature bands are content sections (image + text), not dense admin-style card dashboards. Hero on Start remains brand-first with one headline, one sentence, and CTA group — no feature grid in the first viewport.

### 7. Voice — single Verleiher

**Decision:** Copy addresses the rental customer (“Mieten Sie das Vendiqo-System…”). Do not mention choosing among hire companies. Repeat-rental value: organisation once, events many times.

## Risks / Trade-offs

- **[SMTP ops]** → Misconfigured mail silently drops leads. Mitigate with clear env docs, startup/health warning when inquiry mail is enabled but SMTP incomplete, and backend tests that mock the sender.
- **[Spam]** → Public endpoint attracts bots. Mitigate with honeypot + strict rate limit; add CAPTCHA later only if needed.
- **[Screenshot drift]** → UI changes make marketing images stale. Accept manual refresh; document where assets live and how to recapture.
- **[CORS/CSRF footguns]** → Form fails in prod if origins not allowlisted. Document `ALLOWED_ORIGINS` update as a deploy checklist item; add a small website or backend test for the happy path in CI where feasible.
- **[No lead archive]** → Email-only means no CRM history. Accepted for v1; inbox + mail filters are the system of record.

## Migration Plan

1. Land website pages + assets (can deploy before mail works; form shows friendly error if API/SMTP down)
2. Deploy cloud endpoint + set SMTP and `RENTAL_INQUIRY_TO` secrets
3. Ensure Caddy/prod `ALLOWED_ORIGINS` includes apex/www
4. Update Datenschutz content and replace placeholder contact fields
5. Rollback: revert website image; disable route or unset SMTP to refuse new inquiries

## Open Questions

- Exact inbox address for `RENTAL_INQUIRY_TO` (e.g. `kontakt@vendiqo.ch`) — resolve at apply/deploy time
- Whether development mode logs inquiries to stdout instead of SMTP when unset — recommend yes for local DX
- Whether a CAPTCHA provider is required before go-live — default no; revisit after spam appears
