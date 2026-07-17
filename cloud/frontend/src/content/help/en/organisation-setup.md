Organisations are your hire company's customer mandates. Here you maintain master data, accounting, appliance lending, and payment connections.

## Master data

Under **Organisations** → select organisation → **Master data**:

- Name, address, postal code, city
- **Country** and **currency** (required)
- **Users** — which cloud users have access to this organisation

Currency applies to article prices and event reports for this organisation.

## Accounting

In the **Accounting** section (only visible when enabled):

- **VAT liable** — toggle for VAT treatment
- **Default tax code** — when VAT liable is enabled
- **Enable accounts** — toggle for double-entry bookkeeping
- **Chart of accounts** — create, edit accounts and set default accounts for categories

When accounting is active, a **Bookkeeping** tab appears in running events with export data.

## Appliances

In the **Appliances** tab view and plan lendings for this organisation:

- Current and planned lendings
- **Lend appliances** button for new reservations (hire company admin)

For the read-only member view see **Appliance lending**.

## Card payments (Stripe)

Stripe Connect is set up per organisation. Payouts go to the organisation.

See the **Stripe Connect** help article for onboarding, event activation, and troubleshooting.

## Color palette (app layout)

In the **Color palette (app layout)** tab you define reusable colors for buttons on waiter app layouts:

- Each color has a **label** (e.g. "Bar", "Food", "VIP") and a **color value** (hex)
- Add, edit, or remove colors and apply changes with **Save**
- Up to 32 colors per organisation; duplicate color values are not allowed

In **event configuration** under **App layouts**, these colors appear as quick picks when editing a layout cell — in addition to the free-form color picker. If no palette is defined, only the manual picker is shown.

Cells still store the hex color value; the palette is only a consistent selection aid in the cloud admin UI.

## Who can do what?

- **Hire company admin** — create, delete, and fully manage organisations
- **Organisation admin** — edit assigned organisations (no create/delete)
- **Member** — no access to organisation master data

Roles in detail: **Roles and access**.
