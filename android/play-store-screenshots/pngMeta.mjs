/**
 * Read width/height from a PNG buffer (IHDR chunk).
 * @param {Buffer} buf
 * @returns {{ width: number, height: number }}
 */
export function pngDimensions(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < 24) {
    throw new Error('Not a PNG buffer')
  }
  if (buf.toString('ascii', 1, 4) !== 'PNG') {
    throw new Error('Missing PNG signature')
  }
  return {
    width: buf.readUInt32BE(16),
    height: buf.readUInt32BE(20),
  }
}

/**
 * Play Console tablet screenshot size rules (landscape 16:9).
 * @param {'7in' | '10in'} size
 * @param {number} width
 * @param {number} height
 * @returns {{ ok: boolean, reason?: string }}
 */
export function validatePlayTabletSize(size, width, height) {
  if (width * 9 !== height * 16) {
    return { ok: false, reason: `aspect ${width}x${height} is not 16:9` }
  }
  const min = size === '7in' ? 320 : 1080
  const max = size === '7in' ? 3840 : 7680
  const edge = Math.max(width, height)
  if (edge < min || edge > max) {
    return { ok: false, reason: `${size} edge ${edge} outside ${min}–${max}` }
  }
  return { ok: true }
}

export const EXPECTED_VIEWPORTS = {
  '10in': { width: 1920, height: 1080 },
  '7in': { width: 1280, height: 720 },
}

export const SCREENSHOT_SLUGS = [
  '01-hub',
  '02-events',
  '03-login',
  '04-table-keypad',
  '05-order-empty',
  '06-order-filled',
  '07-open-tables',
  '08-pay-table',
]
