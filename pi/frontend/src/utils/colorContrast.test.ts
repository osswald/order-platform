import { describe, expect, it } from 'vitest'
import { parseHexColor, textColorForBackground } from '@vendiqo/frontend-shared/colorContrast'

describe('parseHexColor', () => {
  it('parses 6-digit hex colors', () => {
    expect(parseHexColor('#0f172a')).toEqual({ r: 15, g: 23, b: 42 })
  })

  it('returns null for invalid input', () => {
    expect(parseHexColor(null)).toBeNull()
    expect(parseHexColor('not-a-color')).toBeNull()
  })
})

describe('textColorForBackground', () => {
  it('picks readable text color for a background', () => {
    expect(textColorForBackground('#ffffff')).toBe('#0f172a')
    expect(textColorForBackground('#000000')).toBe('#ffffff')
  })
})
