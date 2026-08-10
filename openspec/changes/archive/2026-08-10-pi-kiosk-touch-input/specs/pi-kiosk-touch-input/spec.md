## Purpose

Touch-first operator input for daily Pi waiter and cash-register flows: on-screen PIN, money, and digit entry on all appliances, plus platform-aware free-text entry so kiosk screens without a system keyboard remain usable.

## ADDED Requirements

### Requirement: Waiter and register PIN entry uses an on-screen keypad

Waiter login and cash-register login SHALL collect the PIN through an on-screen digit keypad. They MUST NOT rely on a system soft keyboard or hardware keyboard for PIN digits. Selection of waiter / register (and SumUp reader when applicable) remains tap-based as today.

#### Scenario: Waiter enters PIN without system keyboard

- **WHEN** an operator opens waiter login
- **THEN** PIN digits are entered via on-screen keypad buttons
- **AND** no focused native text field is required to enter the PIN

#### Scenario: Register enters PIN without system keyboard

- **WHEN** an operator opens cash-register login
- **THEN** PIN digits are entered via on-screen keypad buttons
- **AND** no focused native text field is required to enter the PIN

### Requirement: PIN login submits only via explicit Anmelden

Waiter and cash-register login SHALL submit only when the operator activates **Anmelden** (or equivalent primary submit control). Reaching a maximum PIN length MUST NOT automatically log in. A wrong PIN SHALL leave the operator on the login screen with an error and SHALL clear or allow clearing the entered digits for retry.

#### Scenario: Explicit submit required

- **WHEN** the operator has entered PIN digits on waiter or register login
- **AND** has not activated Anmelden
- **THEN** the app does not create a waiter or register session

#### Scenario: Wrong PIN stays on login

- **WHEN** the operator activates Anmelden with an incorrect PIN
- **THEN** no session is established
- **AND** an error is shown
- **AND** the operator can enter a new PIN without leaving the screen

### Requirement: Shift cash amounts use on-screen money entry

Shift open and shift close cash-count dialogs SHALL collect the amount through an on-screen money keypad. They MUST NOT require a system keyboard for entering the amount.

#### Scenario: Shift open without system keyboard

- **WHEN** a shift-open dialog asks for Wechselgeld / Kassenbestand
- **THEN** the amount is entered via on-screen money keypad
- **AND** confirming starts the shift using that amount with existing shift semantics

#### Scenario: Shift close without system keyboard

- **WHEN** a shift-close dialog asks for counted cash
- **THEN** the amount is entered via on-screen money keypad
- **AND** confirming closes the shift using that amount with existing shift semantics

### Requirement: Custom percent discount uses on-screen digit entry

When the operator chooses a custom (non-preset) percent discount on order or line discount surfaces, the percent value SHALL be entered through an on-screen digit keypad. Fixed-amount discount mode SHALL continue to use on-screen money entry.

#### Scenario: Custom percent without system keyboard

- **WHEN** the operator selects a custom percent discount
- **THEN** the percent is entered via on-screen digit buttons
- **AND** applying the discount uses existing discount semantics

### Requirement: Non-Android free-text uses an in-app soft keyboard

On Pi frontend clients that are not the Vendiqo Android app, Sammelrechnung name entry and free-text line comments SHALL be entered through an in-app soft keyboard that supports German letters including `ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`, and `ß`. The system IME MUST NOT be required for these fields on those clients.

#### Scenario: Sammelrechnung name on non-Android

- **WHEN** the operator creates a Sammelrechnung name on a non-Android client
- **THEN** text is entered via the in-app soft keyboard
- **AND** confirming creates or assigns the bill with existing semantics

#### Scenario: Line comment on non-Android

- **WHEN** the operator enters a free-text line comment on a non-Android client
- **THEN** text is entered via the in-app soft keyboard
- **AND** saving applies the comment with existing line-position semantics

### Requirement: Android free-text uses the native keyboard

On the Vendiqo Android app, Sammelrechnung name entry and free-text line comments SHALL use the native soft keyboard (IME). The app MUST NOT replace those fields with the in-app soft keyboard on Android. Existing soft-keyboard inset behaviour for text-input sheets remains in effect.

#### Scenario: Sammelrechnung name on Android

- **WHEN** the operator creates a Sammelrechnung name in the Android app
- **THEN** a native text field receives input from the system IME
- **AND** no in-app soft keyboard is shown for that field

#### Scenario: Line comment on Android

- **WHEN** the operator enters a free-text line comment in the Android app
- **THEN** a native text field receives input from the system IME
- **AND** no in-app soft keyboard is shown for that field

### Requirement: Setup and pairing text entry unchanged

Pairing code entry, unpair secret entry, and connection or sync URL fields are out of scope for this capability and SHALL retain their existing input behaviour.

#### Scenario: Pairing still uses existing inputs

- **WHEN** an operator opens Pi pairing or connection setup
- **THEN** those screens are not required to use the in-app soft keyboard introduced by this capability
