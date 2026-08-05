## ADDED Requirements

### Requirement: Immersive Android display routes skip permanent system-bar clearance

When the Pi frontend runs inside the Android WebView in immersive display mode (kitchen, pickup, or register customer display with system bars hidden), those screens SHALL NOT permanently reserve status-bar / navigation-bar safe padding for hidden bars. Waiter and register fullscreen POS screens (order, split-pay, TWINT sheet) that are not immersive SHALL continue to clear system insets as specified by existing safe-layout requirements.

#### Scenario: Immersive kitchen does not keep status-bar gap

- **WHEN** the kitchen monitor is shown on Android with immersive mode active
- **THEN** layout does not permanently pad content by a non-zero `--safe-top` solely for a hidden status bar

#### Scenario: Order screen still clears status bar

- **WHEN** a waiter opens the non-immersive order screen on Android
- **THEN** the order header and primary controls remain fully visible below the status bar and display cutout (unchanged from prior safe-layout behavior)
