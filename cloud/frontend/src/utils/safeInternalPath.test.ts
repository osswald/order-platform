import { describe, expect, it } from 'vitest'
import { safeInternalPath } from './safeInternalPath'

const fallback = '/dashboard'

describe('safeInternalPath', () => {
  it('accepts a same-origin relative path', () => {
    expect(safeInternalPath('/events', fallback)).toBe('/events')
  })

  it('preserves query and hash on a same-origin path', () => {
    expect(safeInternalPath('/events?tab=1#top', fallback)).toBe('/events?tab=1#top')
  })

  it('rejects protocol-relative URLs', () => {
    expect(safeInternalPath('//evil.example', fallback)).toBe(fallback)
    expect(safeInternalPath('//evil.example/phish', fallback)).toBe(fallback)
  })

  it('rejects absolute off-origin URLs', () => {
    expect(safeInternalPath('https://evil.example', fallback)).toBe(fallback)
    expect(safeInternalPath('http://evil.example/x', fallback)).toBe(fallback)
  })

  it('rejects javascript URLs', () => {
    expect(safeInternalPath('javascript:alert(1)', fallback)).toBe(fallback)
  })

  it('rejects backslashes', () => {
    expect(safeInternalPath('/\\evil.example', fallback)).toBe(fallback)
    expect(safeInternalPath('\\evil.example', fallback)).toBe(fallback)
  })

  it('rejects non-strings and empty values', () => {
    expect(safeInternalPath(undefined, fallback)).toBe(fallback)
    expect(safeInternalPath(null, fallback)).toBe(fallback)
    expect(safeInternalPath(1, fallback)).toBe(fallback)
    expect(safeInternalPath('', fallback)).toBe(fallback)
    expect(safeInternalPath(['/events'], fallback)).toBe(fallback)
  })
})
