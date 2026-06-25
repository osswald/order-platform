import { describe, expect, it } from 'vitest'
import { formatDateTime, parseApiDate } from './dateFormat'

describe('parseApiDate', () => {
  it('returns null for empty input', () => {
    expect(parseApiDate(null)).toBeNull()
    expect(parseApiDate('')).toBeNull()
  })

  it('treats timezone-less ISO as UTC', () => {
    const naive = '2026-06-24T15:47:27'
    const aware = '2026-06-24T15:47:27+00:00'
    expect(parseApiDate(naive)?.getTime()).toBe(parseApiDate(aware)?.getTime())
  })

  it('parses Z suffix as UTC', () => {
    expect(parseApiDate('2026-06-24T15:47:27Z')?.getTime()).toBe(
      parseApiDate('2026-06-24T15:47:27+00:00')?.getTime(),
    )
  })
})

describe('formatDateTime', () => {
  it('returns em dash for empty input', () => {
    expect(formatDateTime(null)).toBe('—')
    expect(formatDateTime('')).toBe('—')
  })

  it('formats naive UTC same as explicit UTC offset', () => {
    const naive = formatDateTime('2026-06-24T15:47:27')
    const aware = formatDateTime('2026-06-24T15:47:27+00:00')
    expect(naive).toBe(aware)
    expect(naive).toMatch(/24\.6\.2026/)
  })
})
