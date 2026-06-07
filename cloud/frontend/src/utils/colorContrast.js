const DEFAULT_DARK_TEXT = '#0f172a'
const DEFAULT_LIGHT_TEXT = '#ffffff'

/** @returns {{ r: number, g: number, b: number } | null} */
export function parseHexColor(hex) {
  if (!hex || typeof hex !== 'string') return null
  let value = hex.trim()
  if (!value.startsWith('#')) return null
  value = value.slice(1)
  if (value.length === 3) {
    value = value
      .split('')
      .map((c) => c + c)
      .join('')
  }
  if (value.length === 8) {
    value = value.slice(0, 6)
  }
  if (value.length !== 6 || !/^[0-9a-fA-F]{6}$/.test(value)) return null
  return {
    r: parseInt(value.slice(0, 2), 16),
    g: parseInt(value.slice(2, 4), 16),
    b: parseInt(value.slice(4, 6), 16),
  }
}

/** WCAG 2.x relative luminance for sRGB. */
export function relativeLuminance(r, g, b) {
  const channel = (c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  const rs = channel(r)
  const gs = channel(g)
  const bs = channel(b)
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs
}

function contrastRatio(l1, l2) {
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * Pick light or dark label text for a background hex color.
 * @param {string | null | undefined} hex
 * @param {{ light?: string, dark?: string }} [options]
 */
export function textColorForBackground(hex, options = {}) {
  const light = options.light ?? DEFAULT_LIGHT_TEXT
  const dark = options.dark ?? DEFAULT_DARK_TEXT
  const rgb = parseHexColor(hex)
  if (!rgb) return dark

  const bgLum = relativeLuminance(rgb.r, rgb.g, rgb.b)
  const whiteLum = relativeLuminance(255, 255, 255)
  const darkLum = relativeLuminance(15, 23, 42)

  const whiteContrast = contrastRatio(bgLum, whiteLum)
  const darkContrast = contrastRatio(bgLum, darkLum)
  return whiteContrast >= darkContrast ? light : dark
}
