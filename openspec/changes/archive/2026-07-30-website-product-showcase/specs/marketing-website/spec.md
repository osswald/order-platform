## ADDED Requirements

### Requirement: German-only multi-page marketing site
The public marketing site SHALL be German-only (`lang="de"`) and SHALL expose separate pages for Start, Ablauf, Funktionen, Kontakt (Mietanfrage), and Datenschutz.

#### Scenario: Visitor opens the site home
- **WHEN** a visitor requests `/`
- **THEN** the Start page is served in German with a brand-first hero, a short product pitch, and prominent links or CTAs to Ablauf, Funktionen, and Mietanfrage

#### Scenario: Navigation reaches each marketing page
- **WHEN** a visitor uses the site navigation
- **THEN** they can reach `/ablauf/`, `/funktionen/`, `/kontakt/`, and `/datenschutz/` as distinct pages

### Requirement: Shared chrome and CTA hierarchy
The marketing site SHALL use a shared header and footer across pages. The primary call to action SHALL be Mietanfrage. A link to the cloud Admin UI MAY appear as a secondary action for existing customers.

#### Scenario: Header shows primary rental CTA
- **WHEN** a visitor views any marketing page header
- **THEN** Mietanfrage is presented as the primary navigation action and Admin is not the sole or primary CTA

#### Scenario: Footer includes privacy link
- **WHEN** a visitor views the site footer
- **THEN** a link to Datenschutz is available

### Requirement: Ablauf journey includes setup before on-site ordering
The Ablauf page SHALL present an ordered rental customer journey that starts with organisation setup and event preparation before on-site ordering, payment, and reuse for a subsequent rental.

#### Scenario: Journey order on Ablauf
- **WHEN** a visitor opens `/ablauf/`
- **THEN** the page presents steps in an order that includes organisation setup and event preparation before Bestellen, and includes a later step about reusing the organisation for another event or rental

#### Scenario: Each Ablauf step has short German copy
- **WHEN** a visitor views an Ablauf step
- **THEN** the step has a German headline and a short supporting sentence

### Requirement: Funktionen capability showcase
The Funktionen page SHALL present distinct product capabilities (including Cloud administration, on-site Pi, and Android waiter at minimum) each with a short German headline and one supporting sentence.

#### Scenario: Capabilities are scannable
- **WHEN** a visitor opens `/funktionen/`
- **THEN** they see multiple capability sections that can be scanned without reading a single long narrative

### Requirement: Screenshots with sample data
Ablauf and Funktionen showcase sections that describe product UI SHALL include screenshots that show sample (non-empty, plausible) product data where the UI normally displays data, with German alternative text.

#### Scenario: Screenshot accompanies a UI feature band
- **WHEN** a visitor views a feature or journey band that describes a product UI surface
- **THEN** the band includes a screenshot of that surface with sample data and German `alt` text

### Requirement: Single-Verleiher rental voice
Marketing copy SHALL address prospective rental customers of Vendiqo as the sole Verleiher and SHALL NOT present a multi-hire-company marketplace.

#### Scenario: Home pitch describes renting from Vendiqo
- **WHEN** a visitor reads the Start page pitch
- **THEN** the copy describes renting or using the Vendiqo system for events or venues without asking the visitor to choose among multiple Verleiher
