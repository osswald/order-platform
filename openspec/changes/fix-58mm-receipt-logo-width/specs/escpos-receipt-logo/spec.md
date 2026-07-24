## ADDED Requirements

### Requirement: Logo raster width follows paper preset

The Pi backend SHALL size receipt logo rasters using explicit printable-dot widths for payment-receipt paper presets, not by scaling the 80 mm logo baseline by character column count alone.

#### Scenario: 58 mm logo uses full typical printable width

- **WHEN** a payment receipt ESC/POS payload is built with `paper_width` `58mm` and a wide event logo is enabled
- **THEN** the prepared logo canvas width MUST be 384 dots (unless overridden by env for the default path only)

#### Scenario: 53 mm logo uses narrow preset dots

- **WHEN** a payment receipt ESC/POS payload is built with `paper_width` `53mm` and a wide event logo is enabled
- **THEN** the prepared logo canvas width MUST be 360 dots

#### Scenario: 80 mm logo keeps current default dots

- **WHEN** a payment receipt ESC/POS payload is built with `paper_width` `80mm` and a wide event logo is enabled
- **THEN** the prepared logo canvas width MUST be 384 dots

### Requirement: Logo raster is not padded to 80 mm profile width

When emitting a receipt logo as an ESC/POS bit-image raster, the system MUST NOT horizontally pad the image to the Dummy printer profile media width (TM-T88IV 512 dots). Horizontal placement within the target width MUST be handled by the prepared canvas only.

#### Scenario: 58 mm logo raster byte width matches canvas

- **WHEN** a logo is written for `paper_width` `58mm`
- **THEN** the GS v 0 raster width in the payload MUST equal the prepared canvas width in dots (384), not 512

#### Scenario: Narrow paper logo is not flush-right from profile centering

- **WHEN** a wide logo is rendered for `58mm` or `53mm`
- **THEN** the emitted raster MUST NOT contain profile-centered left/right white padding that would place ink flush to the right edge of a ~384-dot printable head after left-clipping
