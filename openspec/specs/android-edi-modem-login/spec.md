# android-edi-modem-login Specification

## Purpose

Android-only waiter login easter egg: when waiter Edi signs in, show a connecting overlay, briefly play a dial-up modem sample at raised volume, then restore volume and open the waiter hub—without ever blocking login on audio failure.

## Requirements

### Requirement: Trigger on Edi waiter login on Android only

After a successful waiter PIN login in the Pi frontend running inside the Vendiqo Android app, if the waiter display name equals `edi` when compared case-insensitively (leading/trailing whitespace ignored), the app SHALL run the modem handshake easter egg before showing the waiter hub. On non-Android clients, or when the name does not match, login MUST proceed to the hub with no easter egg UI or volume changes.

#### Scenario: Matching name on Android

- **WHEN** a waiter named `Edi` or `edi` (any casing) successfully logs in on Android
- **THEN** the modem handshake easter egg runs before the waiter hub is shown

#### Scenario: Non-matching name

- **WHEN** a waiter with any other name successfully logs in on Android
- **THEN** the app navigates to the waiter hub without the easter egg overlay or modem playback

#### Scenario: Non-Android client

- **WHEN** a waiter named `Edi` successfully logs in in a normal browser (no Android app bridge)
- **THEN** the app navigates to the waiter hub without the easter egg overlay or volume changes

### Requirement: Connecting overlay during handshake

While the easter egg is active, the UI SHALL show a full-viewport overlay with a loading spinner and the text `Connecting...`. The overlay MUST be dismissed when the handshake completes or fails soft.

#### Scenario: Overlay visible during handshake

- **WHEN** the easter egg starts after Edi’s successful login on Android
- **THEN** a full-viewport overlay with a spinner and the text `Connecting...` is visible until the handshake finishes or fails soft

### Requirement: Volume bump, modem playback, and restore

On Android, the easter egg SHALL save the current media stream volume, set media volume to approximately 75% of the stream maximum, play the first 18 seconds of the bundled dial-up modem sample (derived from the public-domain Wikimedia Commons file Dial up modem noises.ogg), and restore the previously saved media volume when playback ends or the easter egg aborts. While the connecting overlay is shown, the soft keyboard SHALL be dismissed so it does not remain visible over the overlay.

#### Scenario: Successful playback restores volume

- **WHEN** the modem sample plays to completion during the easter egg
- **THEN** media volume is restored to the value saved at the start of the easter egg
- **AND** the overlay is dismissed
- **AND** the waiter hub is shown

#### Scenario: Soft keyboard dismissed for overlay

- **WHEN** the easter egg starts after a PIN login that left the soft keyboard open
- **THEN** the soft keyboard is dismissed while the connecting overlay is shown

### Requirement: Soft-fail never blocks login

If modem playback cannot start or fails mid-flight (including missing bundled audio, prepare/play errors, or equivalent), the app MUST restore media volume if it was changed, dismiss the connecting overlay, and still navigate to the waiter hub. The easter egg MUST NOT leave the user stuck on the login screen.

#### Scenario: Missing or unplayable audio

- **WHEN** the easter egg cannot play the modem sample
- **THEN** media volume is restored if it was raised
- **AND** the connecting overlay is dismissed
- **AND** the waiter hub is shown

#### Scenario: Failure after volume was raised

- **WHEN** media volume was set to ~75% and playback then fails
- **THEN** the previously saved media volume is restored before the hub is shown

### Requirement: Attribution for bundled modem sample

The Android app MUST ship a short attribution note for the bundled sample stating the Wikimedia Commons source, author (William Termini), public-domain dedication, and that only the first 18 seconds are included.

#### Scenario: Attribution present in repository or app docs

- **WHEN** a reviewer inspects the Android tree for the modem asset
- **THEN** a short attribution note is present alongside or clearly referencing the bundled sample
