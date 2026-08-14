# pi-android-safe-layout Specification

## Purpose
Android WebView safe-area and fullscreen viewport fill for Pi waiter POS (order, payment, TWINT QR, and related full-bleed surfaces).

## Requirements

### Requirement: Fullscreen POS screens clear Android system insets

When the Pi frontend runs inside the Android WebView (`html.android-app`), fullscreen order and table-payment screens SHALL keep interactive header and content clear of the status bar, display cutout, and navigation bar by applying the inset CSS variables provided by the Android insets bridge (`--safe-top`, `--safe-bottom`).

#### Scenario: Order screen below status bar

- **WHEN** a waiter opens the order screen on Android
- **THEN** the order header and primary controls are fully visible below the system status bar and display cutout

#### Scenario: Payment screen below status bar

- **WHEN** a waiter opens the table payment (split-pay) screen on Android
- **THEN** the payment header and action bars are fully visible within the safe area (not under the status bar or navigation bar)

### Requirement: Fullscreen POS screens fill the Android viewport

On Android, `.order-screen` and `.split-pay-screen` SHALL occupy the full visible height of the WebView (after insets) so flex regions that are designed to share vertical space expand rather than shrink-wrapping to content.

#### Scenario: Order cart and article grid share height

- **WHEN** the order screen is shown on Android with an empty or short cart
- **THEN** the cart region and article grid each receive a substantial share of the viewport height (not a content-sized strip at the top with a large empty void below)

#### Scenario: Payment Rest bar anchors to bottom

- **WHEN** the table payment screen is shown on Android with open lines
- **THEN** the remaining-amount (Rest) bar is anchored at the bottom of the safe viewport and the split panels expand into the space between header and that bar

#### Scenario: Emulated-printer hosted demo

- **WHEN** the Android app is connected to a backend with emulated printer (hosted-demo shell / Belege FAB visible)
- **THEN** order and payment screens still fill the viewport and clear insets as above

### Requirement: TWINT QR sheet clears Android top inset

The TWINT QR fullscreen sheet SHALL apply top and bottom safe-area insets on Android so title, amount, QR, and actions are not obscured by system UI.

#### Scenario: TWINT sheet on real venue Pi

- **WHEN** the waiter completes a TWINT payment path and the QR sheet opens on Android against a real venue Pi
- **THEN** the sheet content starts below the status bar / cutout and remains above the navigation bar safe area

#### Scenario: TWINT sheet actions remain reachable

- **WHEN** the TWINT QR sheet is open on Android
- **THEN** Confirm and Cancel actions are fully tappable within the bottom safe area

### Requirement: TWINT QR sheet fills the Android WebView

The TWINT QR sheet SHALL occupy the full visible height of the Android WebView (after `--safe-top` / `--safe-bottom`), not a partial overlay such as a 70vh bottom sheet. **Fertig** and **Abbrechen** SHALL be pinned to the bottom of that sheet within the bottom safe area. Existing inset clearance for title, amount, and QR MUST remain.

#### Scenario: TWINT sheet is not a partial overlay on Android

- **WHEN** the waiter or register operator opens the TWINT QR sheet on Android
- **THEN** the sheet fills the WebView from the top safe inset to the bottom safe inset
- **AND** the Rest bar and order content underneath are not visible below the sheet

#### Scenario: TWINT Fertig and Abbrechen at bottom on Android

- **WHEN** the TWINT QR sheet is open on Android
- **THEN** **Fertig** and **Abbrechen** are at the bottom of the sheet, fully tappable within the bottom safe area

### Requirement: Non-fullscreen screens remain unchanged

Hub, keypad, list, and settings screens that use normal (non-fullscreen) `app-main` padding SHALL continue to clear the Android top inset via the existing `app-main` padding rule and MUST NOT regress as part of this change.

#### Scenario: Waiter hub still clears status bar

- **WHEN** the waiter hub is shown on Android
- **THEN** the hub title remains clearly below the status bar with the same comfortable top spacing as before this change

### Requirement: Text-input sheets clear the soft keyboard

On Android (and other viewports where the soft keyboard reduces `visualViewport` height), Pi bottom sheets that contain text or numeric inputs SHALL add keyboard-aware bottom spacing so the focused field and primary actions stay visible. This behavior SHALL be limited to those text-input sheets and MUST NOT change layout of bottom sheets that have no text inputs.

#### Scenario: Keyboard open on Sammelrechnung name sheet

- **WHEN** the Sammelrechnung Name sheet is focused on Android and the soft keyboard is visible
- **THEN** the Name field and primary action sit above the keyboard (not under it)

#### Scenario: Payment type picker not lifted by keyboard helper

- **WHEN** a non-text-input bottom sheet such as the payment type picker is open
- **THEN** it continues to use only the existing system safe-area bottom padding and is not offset by the text-input keyboard helper

### Requirement: Immersive Android display routes skip permanent system-bar clearance

When the Pi frontend runs inside the Android WebView in immersive display mode (kitchen, pickup, or register customer display with system bars hidden), those screens SHALL NOT permanently reserve status-bar / navigation-bar safe padding for hidden bars. Waiter and register fullscreen POS screens (order, split-pay, TWINT sheet) that are not immersive SHALL continue to clear system insets as specified by existing safe-layout requirements.

#### Scenario: Immersive kitchen does not keep status-bar gap

- **WHEN** the kitchen monitor is shown on Android with immersive mode active
- **THEN** layout does not permanently pad content by a non-zero `--safe-top` solely for a hidden status bar

#### Scenario: Order screen still clears status bar

- **WHEN** a waiter opens the non-immersive order screen on Android
- **THEN** the order header and primary controls remain fully visible below the status bar and display cutout (unchanged from prior safe-layout behavior)
