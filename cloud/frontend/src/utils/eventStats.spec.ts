import { describe, expect, it } from 'vitest'
import { buildEventStatsPath, clampStatsRange, timelineBucketTooltipTitle } from './eventStats'

describe('buildEventStatsPath', () => {
  it('includes from, to, article_ids, category_ids, and bucket_count query params', () => {
    const from = new Date('2026-06-25T10:00:00.000Z')
    const to = new Date('2026-06-25T12:00:00.000Z')
    const path = buildEventStatsPath(7, from, to, [10, 11], [1, 2], 48)
    expect(path).toContain('/events/7/stats?')
    expect(path).toContain('from=')
    expect(path).toContain('to=')
    expect(path).toContain('article_ids=10')
    expect(path).toContain('article_ids=11')
    expect(path).toContain('category_ids=1')
    expect(path).toContain('category_ids=2')
    expect(path).toContain('bucket_count=48')
  })
})

describe('clampStatsRange', () => {
  it('caps end at now when event is still running', () => {
    const start = new Date('2026-06-25T08:00:00.000Z')
    const end = new Date('2026-06-25T20:00:00.000Z')
    const now = new Date('2026-06-25T12:00:00.000Z')
    const range = clampStatsRange(start, end, now)
    expect(range.from).toEqual(start)
    expect(range.to).toEqual(now)
  })
})

describe('timelineBucketTooltipTitle', () => {
  it('shows times only when bucket start and end are on the same day', () => {
    const title = timelineBucketTooltipTitle(
      [
        {
          start: '2026-06-25T16:35:00.000Z',
          end: '2026-06-25T17:35:00.000Z',
          label: '18:35',
        },
      ],
      0,
      'de',
    )
    expect(title).toContain('–')
    expect(title).not.toMatch(/\d{1,2}\.\d{1,2}\.\d{2,4}/)
  })

  it('shows full date range when bucket spans multiple days', () => {
    const title = timelineBucketTooltipTitle(
      [
        {
          start: '2026-06-25T22:00:00.000Z',
          end: '2026-06-26T02:00:00.000Z',
          label: '00:00',
        },
      ],
      0,
      'de',
    )
    expect(title).toContain('–')
    expect(title.length).toBeGreaterThan(10)
  })
})
