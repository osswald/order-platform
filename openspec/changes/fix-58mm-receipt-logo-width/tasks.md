## 1. Tests first

- [x] 1.1 Update `resolve_logo_max_width` expectations: `80mm`/48 → 384, `58mm` → 384, `53mm` → 360 (replace character-ratio scaling assertions)
- [x] 1.2 Add raster payload tests: for each paper preset with a wide logo, assert GS v 0 width equals preset logo dots and is not 512
- [x] 1.3 Run the new/updated tests and confirm they fail on current `center=True` + scaled-width behavior

## 2. Logo sizing and emit

- [x] 2.1 Add explicit logo-dot presets (or paper_width → dots map) and update `resolve_logo_max_width` / callers that pass `paper_width`
- [x] 2.2 Change `write_logo_bytes` to emit with `center=False` so python-escpos does not pad to TM-T88IV 512
- [x] 2.3 Re-run Pi backend tests for escpos/paper width / payment receipts until green

## 3. Docs and verify

- [x] 3.1 Update `pi/README.md` logo / `ESCPOS_LOGO_MAX_WIDTH` notes to match paper-preset dot widths
- [x] 3.2 Run full Pi backend test suite and `./scripts/lint.sh` for touched areas
