"""Manual QA test case definitions for the full Vendiqo Order Platform."""

from __future__ import annotations

from typing import Callable

TestCase = tuple[str, str, list[str], list[str], list[str]]

FULL_APP_GROUPS: list[tuple[str, Callable[[str], bool]]] = [
    ("Environment baseline", lambda cid: cid.startswith("TC-ENV")),
    ("Cloud — login, roles, org picker", lambda cid: cid.startswith("TC-C-AUTH")),
    ("Cloud — hire companies (platform admin)", lambda cid: cid.startswith("TC-C-HC")),
    ("Cloud — organisations", lambda cid: cid.startswith("TC-C-ORG")),
    ("Cloud — appliances & lendings", lambda cid: cid.startswith("TC-C-APP")),
    ("Cloud — users", lambda cid: cid.startswith("TC-C-USR")),
    ("Cloud — articles & categories", lambda cid: cid.startswith("TC-C-CAT")),
    ("Cloud — waiters", lambda cid: cid.startswith("TC-C-WAI")),
    ("Cloud — dashboard", lambda cid: cid.startswith("TC-C-DASH")),
    (
        "Cloud — event configuration tabs",
        lambda cid: cid.startswith("TC-C-EVTC"),
    ),
    (
        "Cloud — events (stammdaten & workflow)",
        lambda cid: cid.startswith("TC-C-EVT") and not cid.startswith("TC-C-EVTC"),
    ),
    ("Cloud — event reporting", lambda cid: cid.startswith("TC-C-RPT")),
    ("Cloud — Stripe Connect & card payments", lambda cid: cid.startswith("TC-C-STR")),
    ("Cloud — account settings", lambda cid: cid.startswith("TC-C-SET")),
    ("Pi — pairing & setup", lambda cid: cid.startswith("TC-P-SETUP")),
    ("Pi — admin sync & bundle", lambda cid: cid.startswith("TC-P-SYNC")),
    ("Pi — event selection & mode", lambda cid: cid.startswith("TC-P-EVT")),
    ("Pi — waiter hub & shift", lambda cid: cid.startswith("TC-P-WAI")),
    ("Pi — ordering", lambda cid: cid.startswith("TC-P-ORD")),
    ("Pi — open tables", lambda cid: cid.startswith("TC-P-TBL")),
    ("Pi — payments", lambda cid: cid.startswith("TC-P-PAY")),
    ("Pi — collective bills", lambda cid: cid.startswith("TC-P-COL")),
    ("Pi — voucher redeem", lambda cid: cid.startswith("TC-P-VCH")),
    ("Pi — cash register", lambda cid: cid.startswith("TC-P-REG")),
    ("Pi — kitchen & pickup", lambda cid: cid.startswith("TC-P-KIT")),
    ("Pi — stock view", lambda cid: cid.startswith("TC-P-STK")),
    ("Pi — printing", lambda cid: cid.startswith("TC-P-PRT")),
    ("Pi — shifts", lambda cid: cid.startswith("TC-P-SHF")),
    ("Pi — Android printer & terminal", lambda cid: cid.startswith("TC-P-AND")),
    ("End-to-end cross-system", lambda cid: cid.startswith("TC-E2E")),
]

FULL_APP_CASES: list[TestCase] = [
    # --- TC-ENV (2) ---
    (
        "TC-ENV-001",
        "Cloud stack reachable with bootstrap admin",
        [
            "Docker running; cloud compose up (API :8000, frontend :5173)",
            "cloud/.env from example with APP_ENV=development",
        ],
        [
            "1. Open cloud frontend login URL in browser",
            "2. Sign in with ADMIN_EMAIL / ADMIN_PASSWORD from .env",
            "3. Open API /docs when ENABLE_OPENAPI=true",
        ],
        [
            "Login succeeds; dashboard loads without console errors",
            "Bootstrap hire company and admin user exist if DB was fresh",
            "OpenAPI page lists auth and core resources",
        ],
    ),
    (
        "TC-ENV-002",
        "Pi stack reachable unpaired and paired-ready",
        [
            "Pi compose up (API :8001, PWA :5174)",
            "Optional: cloud running for later pairing tests",
        ],
        [
            "1. Open Pi PWA in browser or on device",
            "2. Confirm setup/pairing screen when unpaired",
            "3. Call Pi GET /health or equivalent status endpoint",
        ],
        [
            "PWA loads; shows pairing UI when no appliance credential stored",
            "Pi API responds healthy",
            "No crash loop in Pi backend logs",
        ],
    ),
    # --- TC-C-AUTH (5) ---
    (
        "TC-C-AUTH-001",
        "Valid login and session persistence",
        [
            "Known org user credentials",
            "Cloud frontend on login route",
        ],
        [
            "1. Log in with email and password",
            "2. Refresh the browser page",
            "3. Navigate to Dashboard and Events",
        ],
        [
            "User lands on dashboard after login",
            "Session remains authenticated after refresh",
            "Sidebar shows org-scoped menu items for the user role",
        ],
    ),
    (
        "TC-C-AUTH-002",
        "Invalid credentials rejected",
        ["Cloud login page open"],
        [
            "1. Enter valid email with wrong password",
            "2. Submit login",
            "3. Retry with unknown email",
        ],
        [
            "Login fails with clear error message",
            "User stays on login page; no partial session",
            "No sensitive details leaked in error text",
        ],
    ),
    (
        "TC-C-AUTH-003",
        "Organisation picker scopes data",
        [
            "User with access to two or more organisations",
            "Events or articles exist in each org",
        ],
        [
            "1. Log in and note active organisation in sidebar",
            "2. Switch organisation via picker",
            "3. Open Events list and verify rows",
        ],
        [
            "List updates to selected organisation only",
            "Active org persists on navigation within session",
            "URL/state does not show other org's records",
        ],
    ),
    (
        "TC-C-AUTH-004",
        "Platform admin hire-company picker",
        [
            "Platform admin account",
            "At least two hire companies in cloud",
        ],
        [
            "1. Log in as platform admin",
            "2. Use hire-company picker in sidebar",
            "3. Open Verleiher and tenant-admin areas",
        ],
        [
            "Hire-company picker visible",
            "Switching hire company changes platform-scoped lists",
            "Non-platform users do not see hire-company picker",
        ],
    ),
    (
        "TC-C-AUTH-005",
        "Non-admin blocked from tenant-admin routes",
        [
            "Org user without tenant admin flag",
        ],
        [
            "1. Log in as standard org user",
            "2. Attempt direct navigation to /users and /organisations",
            "3. Attempt /appliances",
        ],
        [
            "Redirects or no-access placeholder for restricted sections",
            "Users menu hidden or disabled in nav",
            "No CRUD API calls succeed for forbidden resources (403)",
        ],
    ),
    # --- TC-C-HC (3) ---
    (
        "TC-C-HC-001",
        "List and create hire company",
        [
            "Platform admin logged in",
            "Unique hire company name prepared",
        ],
        [
            "1. Open Verleiher (hire companies)",
            "2. Create hire company with name and contact fields",
            "3. Save and find row in list",
        ],
        [
            "New hire company appears in table",
            "Detail view opens with saved values",
            "Hire company selectable in platform picker",
        ],
    ),
    (
        "TC-C-HC-002",
        "Edit hire company details",
        [
            "Existing hire company",
            "Platform admin session",
        ],
        [
            "1. Open hire company detail",
            "2. Change display name or contact email",
            "3. Save and reload detail page",
        ],
        [
            "Changes persist after reload",
            "Linked organisations still associated",
            "No validation error on required fields",
        ],
    ),
    (
        "TC-C-HC-003",
        "Hire company context filters platform view",
        [
            "Two hire companies with distinct organisations",
            "Platform admin",
        ],
        [
            "1. Select hire company A in picker",
            "2. Note visible organisations/events",
            "3. Switch to hire company B",
        ],
        [
            "Data sets differ per active hire company",
            "Switch does not leak records across companies",
            "Picker label matches active hire company",
        ],
    ),
    # --- TC-C-ORG (5) ---
    (
        "TC-C-ORG-001",
        "Create organisation under hire company",
        [
            "Tenant admin or platform admin",
            "Active hire company selected",
        ],
        [
            "1. Open Organisations",
            "2. Create organisation with name and currency",
            "3. Save",
        ],
        [
            "Organisation listed and openable in detail",
            "Organisation appears in org picker for permitted users",
            "Defaults applied (e.g. currency) as configured",
        ],
    ),
    (
        "TC-C-ORG-002",
        "Edit organisation settings",
        [
            "Existing organisation",
            "Tenant admin",
        ],
        [
            "1. Open organisation detail",
            "2. Update address or receipt-related org fields",
            "3. Save",
        ],
        [
            "Saved fields shown on reload",
            "Org-scoped cloud pages use updated organisation",
        ],
    ),
    (
        "TC-C-ORG-003",
        "Assign cloud user to organisation",
        [
            "Organisation and spare user email",
            "Tenant admin",
        ],
        [
            "1. Open organisation users/members section",
            "2. Add or link user with role",
            "3. Log in as that user and pick organisation",
        ],
        [
            "User sees organisation in picker after login",
            "Role limits visible menu items appropriately",
        ],
    ),
    (
        "TC-C-ORG-004",
        "Organisation receipt template",
        [
            "Organisation with receipt template editor",
            "Sample logo optional",
        ],
        [
            "1. Open receipt template settings for organisation",
            "2. Edit header/footer lines",
            "3. Save template",
        ],
        [
            "Template saves without error",
            "Pi sync later can apply template on printed receipts (see E2E)",
        ],
    ),
    (
        "TC-C-ORG-005",
        "Organisation appliance lending record",
        [
            "Registered appliance",
            "Organisation and tenant admin",
        ],
        [
            "1. Open organisation lendings or appliance lendings view",
            "2. Create lending linking appliance to organisation",
            "3. Verify lending visible in dashboard/lendings list",
        ],
        [
            "Lending row shows appliance, org, and dates",
            "Appliance available for pairing in Pi when lent to org",
        ],
    ),
    # --- TC-C-APP (5) ---
    (
        "TC-C-APP-001",
        "Register new appliance",
        [
            "Tenant admin",
            "Unique appliance name/identifier",
        ],
        [
            "1. Open Appliances",
            "2. Create appliance record",
            "3. Generate or reveal pairing credential",
        ],
        [
            "Appliance listed with ID",
            "Pairing secret/token shown once or retrievable per UI flow",
            "Credential usable on Pi setup screen",
        ],
    ),
    (
        "TC-C-APP-002",
        "Pair Pi edge device to appliance",
        [
            "Appliance credential from TC-C-APP-001",
            "Pi unpaired on same network",
        ],
        [
            "1. On Pi setup, enter cloud URL and pairing code",
            "2. Complete pairing",
            "3. Confirm cloud appliance shows last-seen or paired state",
        ],
        [
            "Pi shows paired status and admin menu",
            "Cloud appliance record reflects edge connection",
            "Sync enabled when SYNC_ENABLED=1",
        ],
    ),
    (
        "TC-C-APP-003",
        "Lend appliance to organisation",
        [
            "Paired or unpaired appliance",
            "Target organisation",
        ],
        [
            "1. Create appliance lending to organisation with date range",
            "2. Open Appliance lendings list as org user",
        ],
        [
            "Lending visible in cloud lendings view",
            "Org users see appliance in scope for events/sync",
        ],
    ),
    (
        "TC-C-APP-004",
        "Return appliance lending",
        [
            "Active lending on appliance",
        ],
        [
            "1. End or return lending in cloud UI",
            "2. Refresh lendings list",
        ],
        [
            "Lending marked returned/ended",
            "Appliance no longer active for that org period",
        ],
    ),
    (
        "TC-C-APP-005",
        "Revoke pairing and re-pair",
        [
            "Paired Pi appliance",
            "New pairing credential if rotation supported",
        ],
        [
            "1. Unpair from Pi admin or cloud revoke action",
            "2. Confirm Pi returns to setup screen",
            "3. Re-pair with valid credential",
        ],
        [
            "Old token rejected after revoke",
            "Re-pair restores sync and event bundle access",
        ],
    ),
    # --- TC-C-USR (4) ---
    (
        "TC-C-USR-001",
        "Create cloud user with role",
        [
            "Tenant admin",
            "Unique email",
        ],
        [
            "1. Open Users",
            "2. Create user with password and role (admin vs user)",
            "3. Save",
        ],
        [
            "User appears in list",
            "New user can log in with assigned role behavior",
        ],
    ),
    (
        "TC-C-USR-002",
        "Edit user role and org access",
        [
            "Existing non-platform user",
        ],
        [
            "1. Open user detail",
            "2. Change role or organisation memberships",
            "3. Save; log in as user in incognito",
        ],
        [
            "Permissions match updated role",
            "Restricted routes blocked after downgrade",
        ],
    ),
    (
        "TC-C-USR-003",
        "Deactivate or delete user",
        [
            "Disposable test user",
        ],
        [
            "1. Disable or delete user in Users UI",
            "2. Attempt login with that account",
        ],
        [
            "Login fails for removed/disabled user",
            "User removed from pickers and assignment lists",
        ],
    ),
    (
        "TC-C-USR-004",
        "Set Pi admin PIN/code for user",
        [
            "User with Pi admin permission",
            "Paired Pi",
        ],
        [
            "1. Set Pi admin code on user in cloud",
            "2. On Pi, open admin area and enter code",
        ],
        [
            "Pi admin menu unlocks",
            "Wrong code rejected",
        ],
    ),
    # --- TC-C-CAT (5) ---
    (
        "TC-C-CAT-001",
        "Create article category",
        [
            "Active organisation selected",
            "Admin or catalog editor role",
        ],
        [
            "1. Open Article categories",
            "2. Create category with name and sort order",
            "3. Save",
        ],
        [
            "Category listed for organisation",
            "Available when creating articles",
        ],
    ),
    (
        "TC-C-CAT-002",
        "Create article with price and category",
        [
            "At least one category",
        ],
        [
            "1. Open Articles",
            "2. Create article with name, price, category, tax flags as applicable",
            "3. Save",
        ],
        [
            "Article appears in org catalog",
            "Price stored in minor units correctly in UI",
        ],
    ),
    (
        "TC-C-CAT-003",
        "Configure article additions",
        [
            "Base article and addition articles exist",
        ],
        [
            "1. Edit base article",
            "2. Link addition articles with optional/min rules",
            "3. Save",
        ],
        [
            "Additions saved on article",
            "Pi order flow prompts additions picker when article ordered",
        ],
    ),
    (
        "TC-C-CAT-004",
        "Archive or disable article",
        [
            "Article used in past event optional",
        ],
        [
            "1. Mark article inactive/archived per UI",
            "2. Check article list filter",
        ],
        [
            "Article hidden from default active list",
            "Not offered on new event menus after bundle refresh",
        ],
    ),
    (
        "TC-C-CAT-005",
        "Bulk import or duplicate article",
        [
            "Source article with additions",
        ],
        [
            "1. Duplicate article or use copy action if available",
            "2. Rename duplicate and save",
        ],
        [
            "Duplicate has independent ID",
            "Addition links copied or empty per product rules",
        ],
    ),
    # --- TC-C-WAI (3) ---
    (
        "TC-C-WAI-001",
        "Create waiter with PIN",
        [
            "Active organisation",
        ],
        [
            "1. Open Waiters",
            "2. Create waiter display name and PIN",
            "3. Save",
        ],
        [
            "Waiter listed for organisation",
            "PIN usable on Pi waiter login after sync",
        ],
    ),
    (
        "TC-C-WAI-002",
        "Edit waiter and deactivate",
        [
            "Existing waiter",
        ],
        [
            "1. Change name or PIN",
            "2. Deactivate waiter",
            "3. Pull sync on Pi and attempt login",
        ],
        [
            "Updated PIN works when active",
            "Deactivated waiter cannot open shift on Pi",
        ],
    ),
    (
        "TC-C-WAI-003",
        "Waiter visible only in active org",
        [
            "Two organisations with distinct waiters",
        ],
        [
            "1. Select org A; note waiters",
            "2. Switch to org B",
        ],
        [
            "Each org list shows only its waiters",
            "No cross-org waiter IDs in API responses",
        ],
    ),
    # --- TC-C-DASH (3) ---
    (
        "TC-C-DASH-001",
        "Dashboard shows org summary",
        [
            "Org with events and lendings",
            "Org user logged in",
        ],
        [
            "1. Open Dashboard",
            "2. Review widgets/cards for events and appliances",
        ],
        [
            "Counts or lists reflect active organisation only",
            "Links navigate to Events and Appliance lendings",
        ],
    ),
    (
        "TC-C-DASH-002",
        "Appliance lendings read-only view",
        [
            "At least one active lending",
        ],
        [
            "1. Open Appliance lendings from dashboard or menu",
            "2. Filter/search if available",
        ],
        [
            "Lending rows show appliance name, org, status",
            "Org user cannot perform platform-only actions",
        ],
    ),
    (
        "TC-C-DASH-003",
        "Dashboard empty state for new org",
        [
            "Fresh organisation without events",
        ],
        [
            "1. Select new organisation",
            "2. Open Dashboard",
        ],
        [
            "Empty states readable; no errors",
            "CTA or hints point to create event/catalog",
        ],
    ),
    # --- TC-C-EVT (8) ---
    (
        "TC-C-EVT-001",
        "Create event in draft/test status",
        [
            "Organisation with catalog",
            "Admin on cloud",
        ],
        [
            "1. Open Events and create event",
            "2. Set name, dates, currency, status draft or test",
            "3. Save stammdaten",
        ],
        [
            "Event appears in list with correct status chip",
            "Detail opens with stammdaten tabs",
        ],
    ),
    (
        "TC-C-EVT-002",
        "Copy event configuration",
        [
            "Source event with stations and layout",
        ],
        [
            "1. Use copy/duplicate event action",
            "2. Name new event and save",
        ],
        [
            "New event ID created",
            "Stations, layouts, and catalog references copied per rules",
        ],
    ),
    (
        "TC-C-EVT-003",
        "Delete event with confirmation",
        [
            "Disposable test event without production orders",
        ],
        [
            "1. Delete event from list or detail",
            "2. Confirm dialog",
        ],
        [
            "Event removed from list",
            "Pi bundle no longer offers event after sync",
        ],
    ),
    (
        "TC-C-EVT-004",
        "Status workflow draft → test → prod",
        [
            "Event in draft",
            "Validation rules for prod met (dates, config)",
        ],
        [
            "1. Advance status to test",
            "2. Fix any blocking validation messages",
            "3. Advance to prod when allowed",
        ],
        [
            "Status label updates in list",
            "Illegal transitions blocked with message",
            "Prod event eligible for Pi prod selection",
        ],
    ),
    (
        "TC-C-EVT-005",
        "Stammdaten payment mode for waiters",
        [
            "Event detail open",
        ],
        [
            "1. Set payment mode to pay later, pay now, or instant paid",
            "2. Save stammdaten",
            "3. Sync event to Pi and create table order",
        ],
        [
            "Pi enforces pay-later vs pay-now vs instant behavior on submit",
            "Mode persisted after reload",
        ],
    ),
    (
        "TC-C-EVT-006",
        "Payment types cash and card toggles",
        [
            "Event stammdaten Zahlungsarten",
            "Stripe configured if testing card",
        ],
        [
            "1. Enable cash and card payment types",
            "2. Save and sync to Pi",
            "3. Open pay screen on Pi",
        ],
        [
            "Only enabled types offered on Pi pay UI",
            "Disabling card removes terminal/card path",
        ],
    ),
    (
        "TC-C-EVT-007",
        "TWINT and QR display toggles",
        [
            "Event with TWINT enabled in cloud",
            "Pi payment flow",
        ],
        [
            "1. Enable TWINT in event payment settings",
            "2. Save; admin sync on Pi",
            "3. Start TWINT payment on open order",
        ],
        [
            "TWINT QR or deep link shown when enabled",
            "TWINT hidden when disabled in stammdaten",
        ],
    ),
    (
        "TC-C-EVT-008",
        "Archive event status",
        [
            "Completed event eligible for archive",
        ],
        [
            "1. Set status to archive",
            "2. Filter events list by archive",
        ],
        [
            "Archived event hidden from default filters",
            "Historical reports still accessible if supported",
        ],
    ),
    # --- TC-C-EVTC (7) ---
    (
        "TC-C-EVTC-001",
        "Configure kitchen/bar stations",
        [
            "Event detail configuration tab Stations",
        ],
        [
            "1. Add station with name and printer target",
            "2. Map articles to station routes",
            "3. Save event config",
        ],
        [
            "Stations listed on event",
            "Pi routes order lines to station print jobs",
        ],
    ),
    (
        "TC-C-EVTC-002",
        "Assign event waiters",
        [
            "Org waiters exist",
            "Event configuration tab event waiters",
        ],
        [
            "1. Attach waiters to event",
            "2. Save",
            "3. Sync; verify only assigned waiters on Pi",
        ],
        [
            "Assigned waiters can log in on Pi for event",
            "Unassigned waiter rejected or hidden",
        ],
    ),
    (
        "TC-C-EVTC-003",
        "Configure cash registers and layouts",
        [
            "Event tab Registers and Layouts",
        ],
        [
            "1. Create register with layout UUID",
            "2. Place articles and vouchers on layout grid",
            "3. Save",
        ],
        [
            "Register appears in Pi register mode picker",
            "Layout cells match cloud preview",
        ],
    ),
    (
        "TC-C-EVTC-004",
        "Voucher definitions for event",
        [
            "Event vouchers tab",
        ],
        [
            "1. Create voucher definition with value rules",
            "2. Save and sync",
        ],
        [
            "Voucher sale tile on register layout if configured",
            "Redemption available on pay flow",
        ],
    ),
    (
        "TC-C-EVTC-005",
        "App layouts for waiter ordering",
        [
            "Event layouts for waiter mode",
        ],
        [
            "1. Edit waiter layout cells and categories",
            "2. Save",
            "3. Open table order on Pi",
        ],
        [
            "Pi order grid mirrors cloud layout",
            "Stock-limited articles show availability",
        ],
    ),
    (
        "TC-C-EVTC-006",
        "Receipt profiles per station",
        [
            "Event receipts tab",
            "Stations configured",
        ],
        [
            "1. Assign receipt templates per station or register",
            "2. Save",
        ],
        [
            "Guest and kitchen receipts use correct template after print",
        ],
    ),
    (
        "TC-C-EVTC-007",
        "Event stock quantities",
        [
            "Event stock tab",
            "Articles with limited stock",
        ],
        [
            "1. Set stock counts per article",
            "2. Save and sync",
            "3. Order until depleted on Pi",
        ],
        [
            "Pi blocks or warns when stock exhausted",
            "Cloud stock tab shows consumption if updated",
        ],
    ),
    # --- TC-C-RPT (4) ---
    (
        "TC-C-RPT-001",
        "Event Umsatz report",
        [
            "Prod event with payments on Pi",
            "Cloud event reporting Umsatz",
        ],
        [
            "1. Open event reports Umsatz",
            "2. Select date range covering test sales",
        ],
        [
            "Totals match sum of payments within tolerance",
            "Payment method breakdown shown",
        ],
    ),
    (
        "TC-C-RPT-002",
        "Transaktionen list and export",
        [
            "Multiple payments and refunds if any",
        ],
        [
            "1. Open Transaktionen tab",
            "2. Filter by waiter or register if available",
            "3. Export CSV if offered",
        ],
        [
            "Each payment row shows time, amount, method, reference",
            "Export contains same rows as on-screen filter",
        ],
    ),
    (
        "TC-C-RPT-003",
        "Sammelrechnungen (collective invoices)",
        [
            "Collective bills created on Pi",
        ],
        [
            "1. Open Sammelrechnungen report",
            "2. Open detail for one collective bill",
        ],
        [
            "Collective bill totals align with Pi settlement",
            "Linked tables or orders listed",
        ],
    ),
    (
        "TC-C-RPT-004",
        "Schichten (shifts) report",
        [
            "Closed shift on Pi with sales",
        ],
        [
            "1. Open Schichten report for event",
            "2. Compare opening/closing cash totals",
        ],
        [
            "Shift row shows waiter, open/close times",
            "Revenue matches payments during shift window",
        ],
    ),
    # --- TC-C-STR (5) ---
    (
        "TC-C-STR-001",
        "Start Stripe Connect onboarding",
        [
            "Tenant admin",
            "Stripe test mode keys in cloud .env",
        ],
        [
            "1. Open account settings Stripe section",
            "2. Start Connect onboarding",
            "3. Complete Stripe test onboarding flow",
        ],
        [
            "Return URL lands on stripe-connect-return route",
            "Connected account id stored; status shown connected",
        ],
    ),
    (
        "TC-C-STR-002",
        "Refresh expired Connect link",
        [
            "Connect account incomplete or link expired",
        ],
        [
            "1. Open Stripe refresh URL or click refresh in settings",
            "2. Complete Stripe prompt",
        ],
        [
            "User can continue onboarding without error",
            "Settings show updated capability status",
        ],
    ),
    (
        "TC-C-STR-003",
        "Enable card payment type on event",
        [
            "Stripe connected for organisation",
            "Event stammdaten",
        ],
        [
            "1. Enable Karte/card in event payment types",
            "2. Save and sync to Pi",
        ],
        [
            "Pi pay flow offers card/terminal",
            "Missing Connect blocks card with clear message",
        ],
    ),
    (
        "TC-C-STR-004",
        "Card-present payment on Pi terminal",
        [
            "Paired Stripe Terminal or Tap to Pay on Android",
            "Event with card enabled",
        ],
        [
            "1. Create order and open pay",
            "2. Choose card and complete on terminal",
        ],
        [
            "Payment succeeds; receipt offered",
            "Cloud Transaktionen shows card payment",
        ],
    ),
    (
        "TC-C-STR-005",
        "Disconnect or rotate Stripe keys handling",
        [
            "Stripe test dashboard access",
        ],
        [
            "1. Remove or invalidate secret in .env (staging only)",
            "2. Restart cloud backend",
            "3. Attempt card payment",
        ],
        [
            "Cloud logs configuration error; card disabled gracefully",
            "No partial charges without valid Stripe config",
        ],
    ),
    # --- TC-C-SET (2) ---
    (
        "TC-C-SET-001",
        "Change account password",
        [
            "Logged-in user",
            "New password meets policy",
        ],
        [
            "1. Open Account settings",
            "2. Change password with current password confirmation",
            "3. Log out and log in with new password",
        ],
        [
            "Password change succeeds",
            "Old password rejected after change",
        ],
    ),
    (
        "TC-C-SET-002",
        "Account settings profile fields",
        [
            "User with editable profile",
        ],
        [
            "1. Update display name or locale if available",
            "2. Save settings",
        ],
        [
            "Fields persist on reload",
            "Header shows updated email/name",
        ],
    ),
    # --- TC-P-SETUP (3) ---
    (
        "TC-P-SETUP-001",
        "First-time pairing flow",
        [
            "Appliance credential from cloud",
            "Pi on setup screen",
        ],
        [
            "1. Enter cloud base URL",
            "2. Enter pairing code",
            "3. Submit",
        ],
        [
            "Pi shows paired state",
            "Admin sync menu available",
        ],
    ),
    (
        "TC-P-SETUP-002",
        "Invalid pairing code rejected",
        [
            "Pi setup screen",
        ],
        [
            "1. Enter wrong pairing code",
            "2. Submit",
        ],
        [
            "Error toast or message; remains on setup",
            "No partial bundle downloaded",
        ],
    ),
    (
        "TC-P-SETUP-003",
        "Unpair and return to setup",
        [
            "Paired Pi",
            "Pi admin code",
        ],
        [
            "1. Open Pi admin",
            "2. Unpair device",
            "3. Confirm setup screen",
        ],
        [
            "Local credentials cleared",
            "Cloud still shows appliance; re-pair possible",
        ],
    ),
    # --- TC-P-SYNC (4) ---
    (
        "TC-P-SYNC-001",
        "Admin pull sync from cloud",
        [
            "Paired Pi; cloud event in test/prod",
            "Network reachable",
        ],
        [
            "1. Open Pi admin sync",
            "2. Run Pull",
            "3. Open event picker",
        ],
        [
            "Pull completes without error",
            "New/updated event and catalog visible",
        ],
    ),
    (
        "TC-P-SYNC-002",
        "Push local orders to cloud",
        [
            "Offline or queued orders on Pi",
            "Sync enabled",
        ],
        [
            "1. Create order while cloud reachable",
            "2. Run Push from admin sync",
        ],
        [
            "Push reports success count",
            "Cloud Transaktionen shows order/payment",
        ],
    ),
    (
        "TC-P-SYNC-003",
        "Sync status and last error display",
        [
            "Paired Pi",
        ],
        [
            "1. Open sync status panel",
            "2. Induce benign error (wrong cloud URL) then fix",
        ],
        [
            "Status shows last sync time",
            "Error message human-readable; recovers after fix",
        ],
    ),
    (
        "TC-P-SYNC-004",
        "Bundle refresh after cloud config change",
        [
            "Cloud event layout changed",
        ],
        [
            "1. Change layout in cloud",
            "2. Pull on Pi",
            "3. Open order UI",
        ],
        [
            "Pi layout matches cloud without re-pair",
            "Old cached layout not shown",
        ],
    ),
    # --- TC-P-EVT (2) ---
    (
        "TC-P-EVT-001",
        "Select prod event in waiter mode",
        [
            "Paired Pi; prod event synced",
            "Waiter assigned to event",
        ],
        [
            "1. Choose event from Pi event list",
            "2. Select waiter mode (not register)",
            "3. Log in with waiter PIN",
        ],
        [
            "Hub shows tables and open orders entry points",
            "Event name shown in header",
        ],
    ),
    (
        "TC-P-EVT-002",
        "Select event in register mode",
        [
            "Register configured on event",
        ],
        [
            "1. Choose same event in register mode",
            "2. Pick register from list",
        ],
        [
            "Register order layout loads",
            "No waiter PIN required for register flow",
        ],
    ),
    # --- TC-P-WAI (4) ---
    (
        "TC-P-WAI-001",
        "Waiter PIN login",
        [
            "Synced waiter with known PIN",
            "Event selected",
        ],
        [
            "1. Enter waiter PIN on login screen",
            "2. Confirm hub loads",
        ],
        [
            "Correct PIN opens hub",
            "Wrong PIN shows error without lockout excess",
        ],
    ),
    (
        "TC-P-WAI-002",
        "Open shift with float",
        [
            "Waiter logged in",
            "No open shift",
        ],
        [
            "1. Tap open shift",
            "2. Enter opening cash float",
            "3. Confirm",
        ],
        [
            "Shift open indicator visible",
            "Orders allowed",
        ],
    ),
    (
        "TC-P-WAI-003",
        "Hub navigation to tables and orders",
        [
            "Open shift",
        ],
        [
            "1. Open tables list",
            "2. Select table with open order",
            "3. Return to hub",
        ],
        [
            "Navigation works without losing shift",
            "Active table highlighted",
        ],
    ),
    (
        "TC-P-WAI-004",
        "Waiter logout returns to PIN screen",
        [
            "Active waiter session",
        ],
        [
            "1. Log out waiter from hub menu",
        ],
        [
            "PIN entry screen shown",
            "Another waiter can log in",
        ],
    ),
    # --- TC-P-ORD (7) ---
    (
        "TC-P-ORD-001",
        "Create table order from layout",
        [
            "Open shift; pay-later event",
            "Empty table",
        ],
        [
            "1. Select table",
            "2. Add articles from layout cells",
            "3. Submit order",
        ],
        [
            "Order appears on table summary",
            "Kitchen tickets print or queue per station",
        ],
    ),
    (
        "TC-P-ORD-002",
        "Article with additions picker",
        [
            "Article with mandatory additions configured",
        ],
        [
            "1. Tap article on order screen",
            "2. Select additions and confirm",
            "3. Submit line",
        ],
        [
            "Line shows addition labels and price delta",
            "Cannot submit without required additions",
        ],
    ),
    (
        "TC-P-ORD-003",
        "Stock-limited article blocked",
        [
            "Event stock zero for article",
        ],
        [
            "1. Attempt to add depleted article",
        ],
        [
            "Toast or disabled state prevents add",
            "Other articles still orderable",
        ],
    ),
    (
        "TC-P-ORD-004",
        "Sell voucher from layout",
        [
            "Voucher definition on event",
            "Register or waiter layout includes voucher cell",
        ],
        [
            "1. Add voucher line to cart",
            "2. Submit/pay per mode",
        ],
        [
            "Voucher line in basket with correct amount",
            "Voucher code or balance created per backend rules",
        ],
    ),
    (
        "TC-P-ORD-005",
        "Order-level discount",
        [
            "Event allows order discount",
        ],
        [
            "1. Add items",
            "2. Apply order discount percent or amount",
            "3. Submit",
        ],
        [
            "Total reduced correctly",
            "Cloud report shows discounted total",
        ],
    ),
    (
        "TC-P-ORD-006",
        "Line notes and quantity edit",
        [
            "Open order on table",
        ],
        [
            "1. Add line with note",
            "2. Change quantity via modal",
            "3. Submit update",
        ],
        [
            "Note prints on kitchen chit if configured",
            "Quantity reflected in table total",
        ],
    ),
    (
        "TC-P-ORD-007",
        "Pay-now submit opens payment immediately",
        [
            "Event payment mode pay now",
        ],
        [
            "1. Build cart on table",
            "2. Submit order",
        ],
        [
            "Pay screen opens with correct total",
            "Unpaid order not left without payment prompt",
        ],
    ),
    # --- TC-P-TBL (6) ---
    (
        "TC-P-TBL-001",
        "Open tables list shows active orders",
        [
            "Multiple tables with orders",
        ],
        [
            "1. Open tables overview",
            "2. Compare totals with table detail",
        ],
        [
            "Only tables with activity highlighted",
            "Totals match sum of open lines",
        ],
    ),
    (
        "TC-P-TBL-002",
        "Split pay by line groups",
        [
            "Table with several line groups",
            "Pay-later mode",
        ],
        [
            "1. Open table pay / split pay",
            "2. Move lines to basket",
            "3. Settle partial amount",
        ],
        [
            "Partial payment reduces remaining balance",
            "Remaining lines stay open on table",
        ],
    ),
    (
        "TC-P-TBL-003",
        "Transfer table to another number",
        [
            "Order on table A",
            "Empty table B",
        ],
        [
            "1. Open transfer table action",
            "2. Select destination table B",
            "3. Confirm",
        ],
        [
            "Order appears on table B",
            "Table A cleared",
        ],
    ),
    (
        "TC-P-TBL-004",
        "Assign waiter to table",
        [
            "Two waiters with open shifts",
        ],
        [
            "1. Assign table to waiter B",
            "2. Log in as waiter B",
        ],
        [
            "Table visible in waiter B hub",
            "Reporting attributes sales to correct waiter if configured",
        ],
    ),
    (
        "TC-P-TBL-005",
        "Collective assign tables to bill",
        [
            "Collective billing enabled",
            "Multiple tables with orders",
        ],
        [
            "1. Start collective bill",
            "2. Add tables",
            "3. Review collective total",
        ],
        [
            "Combined total equals sum of tables",
            "Collective bill id stable until paid",
        ],
    ),
    (
        "TC-P-TBL-006",
        "Close empty table after pay",
        [
            "Table fully paid",
        ],
        [
            "1. Pay remaining balance",
            "2. Return to tables list",
        ],
        [
            "Table no longer shows open balance",
            "Table available for new order",
        ],
    ),
    # --- TC-P-PAY (6) ---
    (
        "TC-P-PAY-001",
        "Cash payment exact amount",
        [
            "Open order with known total",
            "Cash enabled",
        ],
        [
            "1. Open pay screen",
            "2. Enter exact cash amount",
            "3. Confirm pay",
        ],
        [
            "Payment succeeds toast",
            "Receipt prompt if configured",
            "Table cleared or order closed",
        ],
    ),
    (
        "TC-P-PAY-002",
        "Cash change calculation",
        [
            "Cash payment with amount tendered greater than total",
        ],
        [
            "1. Enter tendered cash above total",
            "2. Complete payment",
        ],
        [
            "Change amount shown correctly",
            "Payment recorded for total due only",
        ],
    ),
    (
        "TC-P-PAY-003",
        "TWINT payment flow",
        [
            "TWINT enabled on event",
            "TWINT test environment",
        ],
        [
            "1. Choose TWINT on pay screen",
            "2. Complete TWINT QR flow",
        ],
        [
            "Payment marked paid on success",
            "TWINT QR hidden after completion",
        ],
    ),
    (
        "TC-P-PAY-004",
        "Pay open order from order list",
        [
            "Pay-later table order unsubmitted payment",
        ],
        [
            "1. Open order from hub",
            "2. Tap pay order",
            "3. Complete cash pay",
        ],
        [
            "Order pay route shows line breakdown",
            "Returns to hub after pay",
        ],
    ),
    (
        "TC-P-PAY-005",
        "Instant paid mode marks lines paid on send",
        [
            "Event payment mode instant paid",
        ],
        [
            "1. Submit new items to table",
        ],
        [
            "No separate pay step for submitted lines",
            "Table total reflects paid lines",
        ],
    ),
    (
        "TC-P-PAY-006",
        "Payment receipt print and skip",
        [
            "Printer configured",
            "Successful payment",
        ],
        [
            "1. Complete payment",
            "2. Accept receipt print",
            "3. Repeat and decline receipt",
        ],
        [
            "Receipt prints on accept",
            "Skip does not block payment completion",
        ],
    ),
    # --- TC-P-COL (3) ---
    (
        "TC-P-COL-001",
        "Create collective bill",
        [
            "Several tables with open orders",
        ],
        [
            "1. Open collective bills",
            "2. Create new bill and add tables",
        ],
        [
            "Collective bill list shows new entry with total",
        ],
    ),
    (
        "TC-P-COL-002",
        "Pay collective bill cash",
        [
            "Open collective bill",
        ],
        [
            "1. Open collective pay",
            "2. Pay full amount cash",
        ],
        [
            "All included tables closed",
            "Cloud Sammelrechnung updated after sync",
        ],
    ),
    (
        "TC-P-COL-003",
        "Remove table from collective before pay",
        [
            "Collective with 2+ tables",
        ],
        [
            "1. Remove one table from collective",
            "2. Verify total recalculates",
        ],
        [
            "Removed table stands alone again",
            "Collective total reduced accordingly",
        ],
    ),
    # --- TC-P-VCH (2) ---
    (
        "TC-P-VCH-001",
        "Redeem voucher on table pay",
        [
            "Valid voucher with balance",
            "Table pay-later order",
        ],
        [
            "1. Open split/table pay",
            "2. Redeem voucher against basket",
            "3. Pay remainder cash",
        ],
        [
            "Voucher credit subtracted from total",
            "Remainder charged correctly",
        ],
    ),
    (
        "TC-P-VCH-002",
        "Voucher redeem on register pay",
        [
            "Register cart with articles",
            "Voucher definition allows redeem",
        ],
        [
            "1. Build register cart",
            "2. Apply voucher redemption",
            "3. Pay payable balance",
        ],
        [
            "Register total shows voucher deduction",
            "Cannot redeem against voucher-only sale if restricted",
        ],
    ),
    # --- TC-P-REG (6) ---
    (
        "TC-P-REG-001",
        "Register mode order from layout",
        [
            "Register selected on prod/test event",
        ],
        [
            "1. Add items via register layout",
            "2. Pay at register",
        ],
        [
            "Order completes without table number",
            "Pickup code generated if enabled",
        ],
    ),
    (
        "TC-P-REG-002",
        "Customer display shows ordering state",
        [
            "Second display or customer display route",
        ],
        [
            "1. Add items on register",
            "2. Observe customer display",
        ],
        [
            "Lines and total mirror register cart",
            "TWINT QR shown on display when applicable",
        ],
    ),
    (
        "TC-P-REG-003",
        "Pickup code printed and called",
        [
            "Event with pickup codes enabled",
        ],
        [
            "1. Complete register order",
            "2. Note pickup code",
            "3. Open pickup screen and mark ready",
        ],
        [
            "Code appears in pickup queue",
            "Customer display updates when called",
        ],
    ),
    (
        "TC-P-REG-004",
        "Register hold and resume pickup",
        [
            "Register order in progress",
        ],
        [
            "1. Hold order on customer display flow",
            "2. Resume and pay",
        ],
        [
            "Cart restored on resume",
            "No duplicate payment on resume pay",
        ],
    ),
    (
        "TC-P-REG-005",
        "Register voucher sale line",
        [
            "Voucher cell on register layout",
        ],
        [
            "1. Sell voucher from register",
            "2. Pay by card or cash",
        ],
        [
            "Voucher sale line separated from food lines",
            "Receipt shows voucher item",
        ],
    ),
    (
        "TC-P-REG-006",
        "Register display idle screen",
        [
            "No active cart",
        ],
        [
            "1. Leave register idle for timeout period",
        ],
        [
            "Customer display shows idle/branding state",
            "New order clears idle",
        ],
    ),
    # --- TC-P-KIT (3) ---
    (
        "TC-P-KIT-001",
        "Kitchen monitor shows new tickets",
        [
            "Station printer or KDS route configured",
            "Submitted order with kitchen items",
        ],
        [
            "1. Open kitchen monitor view",
            "2. Submit order from waiter",
        ],
        [
            "Ticket appears with table, items, notes",
            "Bump/complete removes or dims ticket",
        ],
    ),
    (
        "TC-P-KIT-002",
        "Pickup screen marks order ready",
        [
            "Register order with pickup code",
        ],
        [
            "1. Open pickup screen",
            "2. Mark order ready",
        ],
        [
            "Status changes visible to staff",
            "Customer display shows ready state if linked",
        ],
    ),
    (
        "TC-P-KIT-003",
        "Station filter on kitchen monitor",
        [
            "Multiple stations with orders",
        ],
        [
            "1. Filter kitchen view by station",
        ],
        [
            "Only matching station lines shown",
            "Switching filter updates list immediately",
        ],
    ),
    # --- TC-P-STK (1) ---
    (
        "TC-P-STK-001",
        "Stock view reflects cloud limits",
        [
            "Event with stock counts synced",
        ],
        [
            "1. Open stock view on Pi",
            "2. Sell one unit of limited article",
            "3. Refresh stock view",
        ],
        [
            "Counts decrement locally",
            "Sold-out articles marked unavailable",
        ],
    ),
    # --- TC-P-PRT (4) ---
    (
        "TC-P-PRT-001",
        "Station print on order submit",
        [
            "Printer IP configured in bundle or override",
            "Order with station-routed items",
        ],
        [
            "1. Submit order",
            "2. Verify kitchen printer output",
        ],
        [
            "Chit prints with station name, table, items",
            "Failures queued in print status UI",
        ],
    ),
    (
        "TC-P-PRT-002",
        "Retry failed print job",
        [
            "Simulate printer offline or wrong IP",
        ],
        [
            "1. Submit order to trigger failure",
            "2. Open print failures in admin",
            "3. Fix printer and retry",
        ],
        [
            "Failure listed with error hint",
            "Retry succeeds after printer reachable",
        ],
    ),
    (
        "TC-P-PRT-003",
        "Admin test print",
        [
            "Pi admin access",
            "Printer on network",
        ],
        [
            "1. Open admin printer test",
            "2. Send test print",
        ],
        [
            "Test page prints",
            "Success toast in admin",
        ],
    ),
    (
        "TC-P-PRT-004",
        "Guest receipt after payment",
        [
            "Payment completed",
            "Receipt printer configured",
        ],
        [
            "1. Accept payment receipt",
            "2. Verify receipt content",
        ],
        [
            "Receipt shows items, VAT, payments, org header",
            "QR or TWINT info only if applicable",
        ],
    ),
    # --- TC-P-SHF (3) ---
    (
        "TC-P-SHF-001",
        "Close shift with cash reconciliation",
        [
            "Open shift with cash sales",
        ],
        [
            "1. Open close shift",
            "2. Enter counted cash",
            "3. Confirm close",
        ],
        [
            "Shift closed; hub requires new open shift",
            "Variance shown if counted vs expected differs",
        ],
    ),
    (
        "TC-P-SHF-002",
        "Switch waiter closes previous session",
        [
            "Waiter A logged in with open shift",
        ],
        [
            "1. Log out waiter A",
            "2. Log in waiter B and open shift",
        ],
        [
            "Waiter B shift independent",
            "Waiter A cannot add orders without re-login",
        ],
    ),
    (
        "TC-P-SHF-003",
        "Cannot order without open shift",
        [
            "Waiter logged in, shift closed",
        ],
        [
            "1. Attempt to open table order",
        ],
        [
            "Prompt to open shift first",
            "After opening shift, ordering enabled",
        ],
    ),
    # --- TC-P-AND (5) ---
    (
        "TC-P-AND-001",
        "Android app pairs like PWA",
        [
            "Android build installed",
            "Pairing credential",
        ],
        [
            "1. Open Android app setup",
            "2. Pair to cloud appliance",
        ],
        [
            "Same bundle and events as browser PWA after sync",
        ],
    ),
    (
        "TC-P-AND-002",
        "Android Bluetooth receipt printer",
        [
            "BT printer paired in Android settings",
            "Printer driver enabled in app",
        ],
        [
            "1. Configure printer in app settings",
            "2. Run test print",
            "3. Pay order and print receipt",
        ],
        [
            "BT print succeeds",
            "Receipt matches ESC/POS layout",
        ],
    ),
    (
        "TC-P-AND-003",
        "Android Stripe Terminal Tap to Pay",
        [
            "Stripe Terminal configured",
            "Event card payments enabled",
        ],
        [
            "1. Take card payment on Android",
            "2. Complete on-device reader",
        ],
        [
            "Payment success on Pi",
            "Cloud shows card transaction after push",
        ],
    ),
    (
        "TC-P-AND-004",
        "Android offline queue and sync",
        [
            "Network disabled briefly",
        ],
        [
            "1. Create cash order offline",
            "2. Restore network",
            "3. Push sync",
        ],
        [
            "Order retained locally",
            "Push uploads without duplicate charge",
        ],
    ),
    (
        "TC-P-AND-005",
        "Android kiosk/fullscreen register",
        [
            "Tablet in register mode",
        ],
        [
            "1. Lock to register display route",
            "2. Run full sale cycle",
        ],
        [
            "No accidental navigation out of register",
            "Customer display works on second screen if connected",
        ],
    ),
    # --- TC-E2E (4) ---
    (
        "TC-E2E-001",
        "Cloud config to Pi sale to cloud report",
        [
            "Full stack running",
            "Prod or test event end-to-end",
        ],
        [
            "1. Create article and event in cloud",
            "2. Pull on Pi; sell item for cash",
            "3. Push sync",
            "4. Open cloud Transaktionen",
        ],
        [
            "Sale appears in cloud within expected delay",
            "Amounts and article names match",
        ],
    ),
    (
        "TC-E2E-002",
        "Multi-appliance same event",
        [
            "Two paired Pis on same event",
        ],
        [
            "1. Sell on Pi A table 1",
            "2. Sell on Pi B table 2",
            "3. Push both; view Umsatz",
        ],
        [
            "Both sales aggregated in cloud report",
            "No order id collision",
        ],
    ),
    (
        "TC-E2E-003",
        "Org receipt template on printed receipt",
        [
            "Custom org receipt header in cloud",
            "Pi printed guest receipt",
        ],
        [
            "1. Update org receipt template",
            "2. Pull bundle",
            "3. Complete payment with receipt print",
        ],
        [
            "Printed header/footer matches template",
        ],
    ),
    (
        "TC-E2E-004",
        "Archive event removes from Pi picker",
        [
            "Event used on Pi",
        ],
        [
            "1. Archive event in cloud",
            "2. Pull on Pi",
            "3. Open event list",
        ],
        [
            "Archived event not selectable for new sessions",
            "Existing local data handled per retention rules",
        ],
    ),
]
