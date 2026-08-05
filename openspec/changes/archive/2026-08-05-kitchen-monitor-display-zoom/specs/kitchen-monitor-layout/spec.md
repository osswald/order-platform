## ADDED Requirements

### Requirement: Kitchen monitor uses 80% display zoom

The kitchen monitor root (`KitchenMonitorView`) SHALL apply approximately 80% CSS zoom and compensate width and height so the monitor still fills the available viewport (equivalent to browser zoom at 80%).

#### Scenario: Zoom and compensating size

- **WHEN** the kitchen Bestellungen view is shown
- **THEN** the monitor root uses CSS zoom of 0.8
- **AND** its width and height are scaled by `1 / 0.8` so the visible area fills the viewport

### Requirement: Four ticket columns on tablet landscape under display zoom

With the kitchen display zoom applied, the Bestellungen multi-column layout SHALL fit at least four ticket columns on a typical tablet landscape CSS width of about 1024px (layout width ≈ viewport / 0.8).

#### Scenario: Four columns at 1024 CSS px with 80% zoom

- **WHEN** the kitchen order-columns container layout width corresponds to a 1024 CSS px viewport under 80% display zoom
- **THEN** the column layout computes at least four columns
- **AND** each column width is at least the configured minimum column width

### Requirement: Column gap stays in sync with layout math

Horizontal gap between kitchen order columns SHALL use the shared `KITCHEN_ORDER_GAP_PX` value in both the column-count calculation and the CSS `column-gap`.

#### Scenario: Gap constant drives CSS and layout

- **WHEN** the kitchen order columns render
- **THEN** CSS `--order-gap` matches `KITCHEN_ORDER_GAP_PX`
- **AND** `computeKitchenColumnLayout` uses the same gap when counting columns
