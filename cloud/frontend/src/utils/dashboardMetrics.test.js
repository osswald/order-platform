import { describe, expect, it } from 'vitest'
import {
  attentionItems,
  eventsByStatus,
  eventsStatDetail,
  formatEventDateRange,
  runningEvents,
  statusLabel,
} from './dashboardMetrics'

describe('statusLabel', () => {
  it('maps known statuses and falls back', () => {
    expect(statusLabel('prod')).toBe('Produktivbetrieb')
    expect(statusLabel('unknown')).toBe('unknown')
    expect(statusLabel('')).toBe('—')
  })
})

describe('eventsByStatus', () => {
  it('counts events by status bucket', () => {
    const counts = eventsByStatus([
      { status: 'config' },
      { status: 'prod' },
      { status: 'prod' },
      { status: 'archive' },
    ])
    expect(counts).toEqual({ config: 1, test: 0, prod: 2, archive: 1 })
  })
})

describe('runningEvents', () => {
  const now = new Date('2026-06-04T12:00:00Z')

  it('returns test/prod events within their date window', () => {
    const events = [
      {
        status: 'prod',
        start: '2026-06-04T10:00:00Z',
        end: '2026-06-04T18:00:00Z',
      },
      {
        status: 'config',
        start: '2026-06-04T10:00:00Z',
        end: '2026-06-04T18:00:00Z',
      },
      {
        status: 'test',
        start: '2026-06-05T10:00:00Z',
        end: '2026-06-05T18:00:00Z',
      },
    ]
    expect(runningEvents(events, now)).toHaveLength(1)
    expect(runningEvents(events, now)[0].status).toBe('prod')
  })
})

describe('attentionItems', () => {
  const now = new Date('2026-06-04T12:00:00Z')

  it('flags config events starting within seven days', () => {
    const items = attentionItems(
      [
        {
          id: 1,
          name: 'Sommerfest',
          status: 'config',
          start: '2026-06-08T10:00:00Z',
        },
      ],
      now,
    )
    expect(items).toHaveLength(1)
    expect(items[0].type).toBe('config_starting_soon')
  })

  it('flags TWINT without QR code', () => {
    const items = attentionItems(
      [
        {
          id: 2,
          name: 'Bar',
          status: 'prod',
          payment_types: ['cash', 'twint'],
          has_twint_qr: false,
        },
      ],
      now,
    )
    expect(items).toHaveLength(1)
    expect(items[0].type).toBe('missing_twint_qr')
  })
})

describe('formatEventDateRange', () => {
  it('returns em dash when dates are missing', () => {
    expect(formatEventDateRange(null, null)).toBe('—')
  })

  it('formats a start/end range', () => {
    const range = formatEventDateRange('2026-06-04T10:00:00Z', '2026-06-04T18:00:00Z')
    expect(range).toContain('–')
    expect(range).not.toBe('—')
  })
})

describe('eventsStatDetail', () => {
  it('summarizes running, active, and config counts', () => {
    expect(eventsStatDetail({ test: 1, prod: 2, config: 3 }, 1)).toContain('läuft jetzt')
    expect(eventsStatDetail({ test: 0, prod: 0, config: 0 }, 0)).toBe('Keine Veranstaltungen')
  })
})
