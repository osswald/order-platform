## Context

Payment receipts for Android Bluetooth printers request an ESC/POS payload from the Pi backend with a per-device `paper_width` (`80mm` / `58mm` / `53mm`). Logos are prepared in `escpos_render._prepare_receipt_logo` to a `max_width` canvas, then emitted via `Dummy.image(..., center=True, impl="bitImageRaster")` using the TM-T88IV profile (`media.width.pixels = 512`).

Today `resolve_logo_max_width(line_width)` scales `DEFAULT_MAX_IMAGE_WIDTH` (384) by `line_width / 48`, so 58 mm → 256 dots. With `center=True`, python-escpos pads that canvas to 512 dots. Typical 58 mm printers (~384 printable dots) clip from the left → left whitespace + logo flush-right at ~⅔ width.

## Goals / Non-Goals

**Goals:**

- Logo rasters for paper-width presets MUST NOT be padded to the 80 mm profile width.
- Logo max width for each preset MUST match typical printable dot widths so a wide logo spans the paper.
- Existing ink prep (flatten alpha, threshold, crop bbox, center on canvas) stays; only sizing and ESC/POS emit change.
- Behavior covered by unit tests on raster byte width in the GS v 0 payload.

**Non-Goals:**

- Changing character `PAPER_WIDTH_PRESETS` / line layout for prices.
- Android Bluetooth bridge or paper-width UI.
- Per-printer DPI calibration or custom profiles beyond preset mapping.
- Upscaling tiny logos beyond their native pixel size (still scale down only; span full width when source is wide enough).
- Changing network station slips that omit `paper_width` beyond sharing the safer `center=False` emit if they call the same helper.

## Decisions

### 1. Disable python-escpos image centering

- **Choice:** Call `printer.image(..., center=False)` (default argument or explicit) from `write_logo_bytes`. Keep optional `ESC a` center if useful for text, but do not rely on it for rasters.
- **Why:** `_prepare_receipt_logo` already builds a canvas of the target width. Profile-based `im.center(512)` is the right-align bug on narrow paper.
- **Alternatives considered:** Paper-specific Dummy profiles with matching `media.width.pixels` — more moving parts for the same result; still fragile if profile and canvas disagree.

### 2. Explicit logo dot widths per paper preset

- **Choice:** Resolve logo max width from `paper_width` (or line width via a dedicated map), not `384 * line_width / 48`:

  | Paper | Line chars (unchanged) | Logo max dots |
  |-------|------------------------|---------------|
  | `80mm` | 48 | 384 |
  | `58mm` | 32 | 384 |
  | `53mm` | 30 | 360 |
  | default / no paper | env / 48 chars | `ESCPOS_LOGO_MAX_WIDTH` or 384 |

- **Why:** Common 58 mm Bluetooth heads are ~384 dots; character-column ratio understates physical width. 53 mm stays slightly narrower (~360) for devices that need the existing “narrow” preset. 80 mm keeps today’s 384 default (already used with TM-T88IV centering historically).
- **Alternatives considered:** Scale from 512 (true TM-T88IV width) — would widen network logos and risk `ImageWidthError` or overflow on 384-dot 80 mm devices; out of scope. Keep 256 for 58 mm after only fixing center — fixes alignment but not “span whole width.”

### 3. API shape

- Prefer `resolve_logo_max_width(paper_width: str | None = None, *, line_width: int | None = None)` or a small `LOGO_WIDTH_PRESETS` dict keyed like `PAPER_WIDTH_PRESETS`, with callers that already have `paper_width` passing it through (`build_payment_receipt_text` already has it).
- Keep `ESCPOS_LOGO_MAX_WIDTH` as override for the default/no-preset path only (or as a hard cap) — document in `pi/README.md`.

### 4. Tests first

- Assert GS v 0 `width_bytes` for a full-bleed black logo equals `ceil(max_dots / 8)` for each preset, and that width is **not** 64 (512 dots) when centering is off.
- Update `test_resolve_logo_max_width_scales_with_line_width` to the new mapping.

## Risks / Trade-offs

- [Some 58 mm printers have &lt;384 printable dots] → Mitigation: 384 matches current 80 mm default and common BT hardware; 53 mm preset remains for narrower devices; operators can pick 53 mm if clipped.
- [80 mm logos previously visually centered via 512 pad] → Mitigation: canvas is already full `max_width`; without profile pad, 384-dot logo prints left-origin on a 512-dot head (small left bias vs true center). Acceptable vs broken 58 mm; revisit only if 80 mm network logos look wrong.
- [Very narrow artwork] → Mitigation: unchanged — cropped and centered on canvas, not stretched up.

## Migration Plan

- Deploy Pi backend only; no DB/migration. Rollback = previous image.
- No client changes; existing `paper_width` request field unchanged.

## Open Questions

- None blocking: 58→384 and 53→360 are the explore-mode defaults; adjust in implementation if a device in the field needs different values.
