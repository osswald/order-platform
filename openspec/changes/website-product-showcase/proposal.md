## Why

The public site at vendiqo.ch is a single German hero with almost no product story. Prospective rental customers cannot see how Vendiqo works (organisation and event setup before on-site ordering), what the surfaces look like, or request a rental. Expanding the marketing site into a multi-page German showcase with screenshots and a Mietanfrage form turns the apex domain into a real Verleih acquisition surface.

## What Changes

- Expand the static marketing site (`website/`) into several German-only pages: Start, Ablauf, Funktionen, Kontakt (Mietanfrage), plus existing Datenschutz
- Tell the rental customer journey starting with organisation and event setup (not only Bestellen), including reuse for repeat rentals
- Show product screenshots with sample data and short accompanying texts on Ablauf and Funktionen
- Add a Mietanfrage contact form that delivers inquiries by email only (no lead database)
- Shift primary CTA from Admin to Mietanfrage; keep Admin as a secondary nav link for existing customers
- Update Datenschutz for contact/inquiry processing and real contact placeholders where needed
- Voice assumes a single Verleiher (Vendiqo GmbH), not a multi-hire-company marketplace

## Capabilities

### New Capabilities

- `marketing-website`: Multi-page German public marketing site (navigation, Start, Ablauf, Funktionen, shared layout/content patterns, screenshot showcase)
- `rental-inquiry`: Public Mietanfrage form with validation, spam protection, and email-only delivery to Vendiqo

### Modified Capabilities

- (none — no existing marketing-site specs)

## Impact

- **Code**: `website/` (HTML pages, CSS, layout JS, Vite multi-page inputs, nginx routes); likely a small public API endpoint or form-mail integration for email delivery
- **Content/assets**: New German copy; product screenshots (reuse/adapt Play Store captures; add Cloud setup shots as needed) under `website/public/` or similar
- **Privacy**: `website/content/datenschutz.md` must cover inquiry processing and contact details
- **Ops**: SMTP or form-to-email configuration (env secrets); no CRM/DB pipeline in v1
- **Out of scope**: English locale, multi-Verleiher marketplace, admin lead inbox UI, pricing page, live product demo embed
