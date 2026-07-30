## ADDED Requirements

### Requirement: Text-input sheets clear the soft keyboard

On Android (and other viewports where the soft keyboard reduces `visualViewport` height), Pi bottom sheets that contain text or numeric inputs SHALL add keyboard-aware bottom spacing so the focused field and primary actions stay visible. This behavior SHALL be limited to those text-input sheets and MUST NOT change layout of bottom sheets that have no text inputs.

#### Scenario: Keyboard open on Sammelrechnung name sheet

- **WHEN** the Sammelrechnung Name sheet is focused on Android and the soft keyboard is visible
- **THEN** the Name field and primary action sit above the keyboard (not under it)

#### Scenario: Payment type picker not lifted by keyboard helper

- **WHEN** a non-text-input bottom sheet such as the payment type picker is open
- **THEN** it continues to use only the existing system safe-area bottom padding and is not offset by the text-input keyboard helper
