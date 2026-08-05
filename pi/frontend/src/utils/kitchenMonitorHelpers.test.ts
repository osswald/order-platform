import { describe, expect, it } from 'vitest'
import type { KitchenOrderTicket } from '@/types/api'
import {
  computeKitchenColumnLayout,
  formatElapsedMinutes,
  KITCHEN_DISPLAY_ZOOM,
  KITCHEN_MIN_COLUMN_WIDTH_PX,
  KITCHEN_ORDER_GAP_PX,
  kitchenArticleDisplayName,
  kitchenLayoutWidthForViewport,
  kitchenLineAdditionLabels,
  sortTicketsByWaitTime,
  ticketElapsedMs,
  ticketStatusLabel,
  ticketUrgencyLevel,
} from './kitchenMonitorHelpers'

function ticket(overrides: Partial<KitchenOrderTicket> = {}): KitchenOrderTicket {
  return {
    id: 1,
    lines: [],
    status: 'open',
    ordered_at: '2026-01-01T12:00:00.000Z',
    ...overrides,
  } as KitchenOrderTicket
}

describe('sortTicketsByWaitTime', () => {
  it('sorts oldest ordered_at first', () => {
    const sorted = sortTicketsByWaitTime([
      ticket({ id: 2, ordered_at: '2026-01-01T12:10:00.000Z' }),
      ticket({ id: 1, ordered_at: '2026-01-01T12:00:00.000Z' }),
    ])
    expect(sorted.map((row) => row.id)).toEqual([1, 2])
  })
})

describe('ticketUrgencyLevel', () => {
  it('returns red after 10 minutes', () => {
    const now = Date.parse('2026-01-01T12:11:00.000Z')
    expect(ticketUrgencyLevel(ticket(), now)).toBe('red')
  })

  it('returns green under 5 minutes', () => {
    const now = Date.parse('2026-01-01T12:03:00.000Z')
    expect(ticketUrgencyLevel(ticket(), now)).toBe('green')
  })
})

describe('ticketElapsedMs', () => {
  it('computes elapsed from ordered_at', () => {
    const now = Date.parse('2026-01-01T12:05:00.000Z')
    expect(ticketElapsedMs(ticket(), now)).toBe(5 * 60 * 1000)
  })
})

describe('formatElapsedMinutes', () => {
  it('formats short waits in minutes', () => {
    expect(formatElapsedMinutes(3 * 60 * 1000)).toBe('3 min')
  })
})

describe('computeKitchenColumnLayout', () => {
  it('fills the container width without leftover horizontal space', () => {
    const { columnCount, columnWidthPx } = computeKitchenColumnLayout(1600)
    expect(columnCount * columnWidthPx + (columnCount - 1) * KITCHEN_ORDER_GAP_PX).toBeCloseTo(1600, 5)
  })

  it('uses at least one column on narrow containers', () => {
    expect(computeKitchenColumnLayout(200).columnCount).toBe(1)
  })

  it('fits four columns on tablet landscape at 80% display zoom', () => {
    expect(KITCHEN_DISPLAY_ZOOM).toBe(0.8)
    // ~1024 CSS px tablet width → layout width under 80% zoom compensation
    const layoutWidth = kitchenLayoutWidthForViewport(1024)
    const { columnCount, columnWidthPx } = computeKitchenColumnLayout(layoutWidth)
    expect(columnCount).toBeGreaterThanOrEqual(4)
    expect(columnWidthPx).toBeGreaterThanOrEqual(KITCHEN_MIN_COLUMN_WIDTH_PX)
  })

  it('respects the minimum column width when there is room', () => {
    const { columnWidthPx } = computeKitchenColumnLayout(1600)
    expect(columnWidthPx).toBeGreaterThanOrEqual(KITCHEN_MIN_COLUMN_WIDTH_PX)
  })
})

describe('ticketStatusLabel', () => {
  it('maps backend statuses to German labels', () => {
    expect(ticketStatusLabel('partial')).toBe('Teilweise')
    expect(ticketStatusLabel('open')).toBe('Neu')
  })
})

describe('kitchenLineAdditionLabels', () => {
  const articles = {
    '30': { name: 'Gemischter Salat', label: 'Salat' },
    '31': { name: 'Grüner Salat' },
  }

  it('returns one label per addition', () => {
    expect(
      kitchenLineAdditionLabels(
        {
          additions: [
            { article_id: 30, qty: 1, name: 'mit Gemischter Salat' },
            { article_id: 31, qty: 1, name: 'mit Grüner Salat' },
          ],
        },
        articles,
      ),
    ).toEqual(['+ 1x Salat', '+ 1x mit Grüner Salat'])
  })

  it('prefers catalog label over line name and catalog name', () => {
    expect(
      kitchenLineAdditionLabels(
        { additions: [{ article_id: 30, qty: 1, name: 'mit Gemischter Salat' }] },
        articles,
      ),
    ).toEqual(['+ 1x Salat'])
  })

  it('resolves names from the article catalog when missing on the line', () => {
    expect(kitchenLineAdditionLabels({ additions: [{ article_id: 30, qty: 2 }] }, articles)).toEqual([
      '+ 2x Salat',
    ])
  })
})

describe('kitchenArticleDisplayName', () => {
  it('prefers label over name and fallback', () => {
    expect(
      kitchenArticleDisplayName(10, { '10': { name: 'Burger Deluxe', label: 'Burger' } }, 'Snap'),
    ).toBe('Burger')
  })

  it('falls back to name when label empty', () => {
    expect(kitchenArticleDisplayName(10, { '10': { name: 'Raclette', label: '' } })).toBe('Raclette')
  })
})
