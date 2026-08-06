## REMOVED Requirements

### Requirement: Kitchen monitor uses 80% display zoom

**Reason**: CSS zoom with compensating width broke Produkte flex-wrap and clipped kitchen header controls.

**Migration**: Density via lower `KITCHEN_MIN_COLUMN_WIDTH_PX` (and existing column gap) without changing containing-block width; no CSS `zoom` on the kitchen root.

### Requirement: Four ticket columns on tablet landscape under display zoom

**Reason**: Replaced by the same four-column goal measured against the real (non-zoom-compensated) container width.

**Migration**: Use “Four ticket columns on tablet landscape without zoom”.

## ADDED Requirements

### Requirement: Kitchen monitor fills the viewport without CSS zoom

The kitchen monitor root SHALL fill the available viewport using normal width/height (e.g. 100% / `100dvh`) and MUST NOT use CSS `zoom` (or equivalent scale-with-compensating-size) that inflates the layout containing block beyond the visible viewport.

#### Scenario: No kitchen CSS zoom

- **WHEN** the kitchen Bestellungen or Produkte view is shown
- **THEN** the monitor root does not apply CSS `zoom` with a compensating width/height larger than the viewport

#### Scenario: Header controls remain visible

- **WHEN** the kitchen monitor header is shown on tablet or desktop
- **THEN** the Bestellungen / Produkte toggle and Aktualisieren control are fully visible within the viewport (not clipped off the right edge)

### Requirement: Four ticket columns on tablet landscape without zoom

The Bestellungen multi-column layout SHALL fit at least four ticket columns on a typical tablet landscape CSS width of about 1024px, using the real container width (not a zoom-compensated wider layout box).

#### Scenario: Four columns at 1024 CSS px

- **WHEN** `computeKitchenColumnLayout` is given a container width of 1024px
- **THEN** the computed column count is at least four
- **AND** each column width is at least the configured minimum column width

### Requirement: Produkte wrap within the viewport

Kitchen Produkte cards SHALL wrap to additional rows within the visible kitchen body width. Horizontal clipping that hides cards off the right edge instead of wrapping MUST NOT occur under normal browser page zoom.

#### Scenario: Product cards wrap

- **WHEN** the Produkte view has more cards than fit on one row of the visible kitchen body
- **THEN** additional cards wrap to the next row within the visible width
- **AND** cards are not solely clipped away to the right by overflow

### Requirement: Column gap stays in sync with layout math

Horizontal gap between kitchen order columns SHALL use the shared `KITCHEN_ORDER_GAP_PX` value in both the column-count calculation and the CSS `column-gap`.

#### Scenario: Gap constant drives CSS and layout

- **WHEN** the kitchen order columns render
- **THEN** CSS `--order-gap` matches `KITCHEN_ORDER_GAP_PX`
- **AND** `computeKitchenColumnLayout` uses the same gap when counting columns
