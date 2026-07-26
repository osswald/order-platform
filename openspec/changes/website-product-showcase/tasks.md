## 1. Public rental-inquiry API (cloud)

- [x] 1.1 Write backend tests for `POST /public/rental-inquiry`: valid payload triggers send, missing fields → 4xx, invalid email → 4xx, honeypot filled → no send, rate limit returns 429
- [x] 1.2 Add Pydantic schema, mail helper (SMTP from env; dev log fallback when SMTP unset), and public router with rate limit
- [x] 1.3 Wire router in `main.py`; document env vars (`SMTP_*`, `RENTAL_INQUIRY_TO`, `ALLOWED_ORIGINS` must include apex/www)
- [x] 1.4 Export OpenAPI and regenerate cloud frontend API types if the public path is included in the shared schema export
- [x] 1.5 Run cloud backend tests for the new inquiry suite

## 2. Marketing site structure and chrome

- [x] 2.1 Add Vite MPA inputs and HTML shells for `/ablauf/`, `/funktionen/`, `/kontakt/`
- [x] 2.2 Update shared `layout.js` nav: Ablauf, Funktionen, Mietanfrage (primary), Admin secondary; footer Datenschutz
- [x] 2.3 Expand `styles.css` for multi-section pages, feature bands (image + text), form, and CTAs while keeping German marketing voice and light visual tokens
- [x] 2.4 Rewrite Start (`index.html`) hero: brand-first, Verleih pitch, teasers to Ablauf / Funktionen / Mietanfrage

## 3. Content pages and screenshots

- [x] 3.1 Collect screenshot assets into `website/public/images/` (reuse Play Store Android shots; capture Cloud org/event sample-data shots)
- [x] 3.2 Implement `/ablauf/` journey bands in order: Organisation → Event → Bestellen → Küche → Zahlen → Wiederverwenden (headline + one sentence + screenshot each)
- [x] 3.3 Implement `/funktionen/` capability bands (Cloud, Pi, Android, Zahlungen, Belege at minimum) with short DE copy + screenshots
- [x] 3.4 Add German `alt` text for all showcase images

## 4. Kontakt form (website)

- [x] 4.1 Build `/kontakt/` form UI (required/optional fields per spec, honeypot, Datenschutz link)
- [x] 4.2 Add client JS to POST to the public API (configurable API base), show success confirmation or German error states
- [x] 4.3 Add a small website test or smoke check for form markup / client validation behavior where the existing website toolchain allows

## 5. Privacy and deploy checklist

- [x] 5.1 Update `website/content/datenschutz.md` for Mietanfragen (email processing purpose) and replace placeholder contact fields where known
- [x] 5.2 Note prod checklist: SMTP secrets, `RENTAL_INQUIRY_TO`, `ALLOWED_ORIGINS` includes `https://vendiqo.ch` and `https://www.vendiqo.ch`
- [x] 5.3 Run website build; run lint for touched areas; run relevant cloud backend tests

## 6. Verification

- [x] 6.1 Manually verify page set and nav on desktop and mobile widths
- [x] 6.2 Manually verify inquiry happy path against local/dev API (or logged fallback) and confirm no DB lead row is created
