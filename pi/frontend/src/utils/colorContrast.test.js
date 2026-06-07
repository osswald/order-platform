import { describe, expect, it } from 'vitest'
import { parseHexColor, textColorForBackground } from './colorContrast'

describe('parseHexColor', () => {
  it('parses 6-digit hex', () => {
    expect(parseHexColor('#334155')).toEqual({ r: 51, g: 65, b: 85 })
  })

  it('parses 3-digit hex', () => {
    expect(parseHexColor('#eee')).toEqual({ r: 238, g: 238, b: 238 })
  })

  it('ignores alpha channel', () => {
    expect(parseHexColor('#334155ff')).toEqual({ r: 51, g: 65, b: 85 })
  })

  it('returns null for invalid values', () => {
    expect(parseHexColor('')).toBeNull()
    expect(parseHexColor('334155')).toBeNull()
    expect(parseHexColor('#gggggg')).toBeNull()
  })
})

describe('textColorForBackground', () => {
  it('uses dark text on light backgrounds', () => {
    expect(textColorForBackground('#eeeeee')).toBe('#0f172a')
    expect(textColorForBackground('#ffffff')).toBe('#0f172a')
  })

  it('uses light text on dark backgrounds', () => {
    expect(textColorForBackground('#334155')).toBe('#ffffff')
    expect(textColorForBackground('#000000')).toBe('#ffffff')
  })

  it('falls back to dark text for invalid input', () => {
    expect(textColorForBackground('')).toBe('#0f172a')
    expect(textColorForBackground(null)).toBe('#0f172a')
    expect(textColorForBackground('not-a-color')).toBe('#0f172a')
  })
})
