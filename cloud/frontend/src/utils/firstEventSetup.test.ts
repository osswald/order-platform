import { describe, expect, it } from 'vitest'
import {
  firstEventSetupCtaVisible,
  firstEventSetupIsContinue,
  firstEventSetupWizardRoute,
  resolveFirstEventSetupStep,
  suggestLayoutCells,
  suggestLayoutGrid,
} from './firstEventSetup'

describe('firstEventSetup', () => {
  it('shows CTA only when available', () => {
    expect(firstEventSetupCtaVisible({ available: true, completed: false, dismissed: false, in_progress_event_id: null })).toBe(true)
    expect(firstEventSetupCtaVisible({ available: false, completed: true, dismissed: false, in_progress_event_id: null })).toBe(false)
    expect(firstEventSetupCtaVisible(null)).toBe(false)
  })

  it('detects continue vs start', () => {
    expect(
      firstEventSetupIsContinue({
        available: true,
        completed: false,
        dismissed: false,
        in_progress_event_id: 9,
      }),
    ).toBe(true)
    expect(
      firstEventSetupIsContinue({
        available: true,
        completed: false,
        dismissed: false,
        in_progress_event_id: null,
      }),
    ).toBe(false)
  })

  it('builds wizard route with organisation query', () => {
    expect(firstEventSetupWizardRoute(3, 'station')).toEqual({
      name: 'first-event-setup',
      query: { organisationId: '3', step: 'station' },
    })
  })

  it('resolves resume step from progress', () => {
    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 0,
        waiterCount: 0,
        inProgressEventId: null,
        hasStationWithArticles: false,
        hasEventWaiter: false,
        hasAppLayout: false,
      }),
    ).toBe('menu')

    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 2,
        waiterCount: 0,
        inProgressEventId: null,
        hasStationWithArticles: false,
        hasEventWaiter: false,
        hasAppLayout: false,
      }),
    ).toBe('waiters')

    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 2,
        waiterCount: 1,
        inProgressEventId: null,
        hasStationWithArticles: false,
        hasEventWaiter: false,
        hasAppLayout: false,
      }),
    ).toBe('event')

    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 2,
        waiterCount: 1,
        inProgressEventId: 5,
        hasStationWithArticles: false,
        hasEventWaiter: true,
        hasAppLayout: false,
      }),
    ).toBe('station')

    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 2,
        waiterCount: 1,
        inProgressEventId: 5,
        hasStationWithArticles: true,
        hasEventWaiter: true,
        hasAppLayout: false,
      }),
    ).toBe('layout')

    expect(
      resolveFirstEventSetupStep({
        sellableArticleCount: 2,
        waiterCount: 1,
        inProgressEventId: 5,
        hasStationWithArticles: true,
        hasEventWaiter: true,
        hasAppLayout: true,
      }),
    ).toBe('done')
  })

  it('suggests layout cells from articles', () => {
    expect(suggestLayoutGrid(1)).toEqual({ width: 2, height: 2 })
    const cells = suggestLayoutCells([
      { id: 1, name: 'Beer', label: 'Beer' },
      { id: 2, name: 'Wine', label: 'Wine' },
    ])
    expect(cells).toHaveLength(2)
    expect(cells[0]).toMatchObject({ row: 0, col: 0, article_ids: [1], label: 'Beer' })
    expect(cells[1]).toMatchObject({ row: 0, col: 1, article_ids: [2], label: 'Wine' })
  })
})
