## ADDED Requirements

### Requirement: TWINT QR sheet fills the Android WebView

The TWINT QR sheet SHALL occupy the full visible height of the Android WebView (after `--safe-top` / `--safe-bottom`), not a partial overlay such as a 70vh bottom sheet. **Fertig** and **Abbrechen** SHALL be pinned to the bottom of that sheet within the bottom safe area. Existing inset clearance for title, amount, and QR MUST remain.

#### Scenario: TWINT sheet is not a partial overlay on Android

- **WHEN** the waiter or register operator opens the TWINT QR sheet on Android
- **THEN** the sheet fills the WebView from the top safe inset to the bottom safe inset
- **AND** the Rest bar and order content underneath are not visible below the sheet

#### Scenario: TWINT Fertig and Abbrechen at bottom on Android

- **WHEN** the TWINT QR sheet is open on Android
- **THEN** **Fertig** and **Abbrechen** are at the bottom of the sheet, fully tappable within the bottom safe area
