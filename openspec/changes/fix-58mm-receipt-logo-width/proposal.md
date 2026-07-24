## Why

On 58 mm Bluetooth payment receipts the event logo prints flush-right and undersized instead of spanning the printable width. python-escpos centers rasters against the TM-T88IV 80 mm profile (512 dots) while logo max-width is scaled from character columns (256 dots for 58 mm). Narrow printers clip that padded raster from the left, so the logo looks right-aligned and only about two-thirds wide.

## What Changes

- Stop re-centering logo rasters with the 80 mm Epson profile width when emitting ESC/POS image commands (canvas already sizes/centers ink for the target width).
- Map receipt `paper_width` presets to explicit logo max widths in dots so 58 mm / 53 mm logos fill typical Bluetooth printable widths (~384 / ~360 dots), not a character-column ratio off an 80 mm baseline.
- Keep network/station slips (no `paper_width`) on the existing default logo width behavior unless they share the same renderer path—no API or UI changes.
- Add/extend Pi backend tests that assert raster byte-width for each paper preset and that centered profile padding is not applied.

## Capabilities

### New Capabilities

- `escpos-receipt-logo`: ESC/POS receipt logo raster sizing and horizontal placement for paper-width presets (Bluetooth payment receipts and any slip that passes `paper_width`).

### Modified Capabilities

- (none)

## Impact

- Pi backend: `escpos_render.py` (`resolve_logo_max_width`, `write_logo_bytes` / `_prepare_receipt_logo`), callers in `print_worker.py` that pass logo width from paper width
- Pi backend tests: `test_escpos_paper_width.py`, `test_escpos_render.py` (and payment-receipt coverage if needed)
- Docs: `pi/README.md` logo / `ESCPOS_LOGO_MAX_WIDTH` notes if they describe the old scaling rule
- No cloud API, Android bridge, or frontend paper-width UI changes
