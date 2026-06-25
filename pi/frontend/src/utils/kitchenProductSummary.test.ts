import { describe, expect, it } from 'vitest'
import type { EdgeBundleEvent, KitchenOrderTicket } from '@/types/api'
import { buildKitchenProductSummary, kitchenProductLocationShortLabel } from './kitchenProductSummary'

const event = {
  articles: {
    '10': { id: 10, name: 'Burger', price: 12, additions: [] },
    '20': { id: 20, name: 'Bier', price: 5, additions: [] },
    '30': { id: 30, name: 'Salat', price: 2, additions: [] },
  },
  configuration: {
    app_layouts: [
      {
        uuid: 'layout-1',
        is_default: true,
        cells: [
          { row: 0, col: 0, label: 'Food', color: '#fef08a', article_ids: [10] },
          { row: 1, col: 0, label: 'Drinks', color: '#bfdbfe', article_ids: [20] },
          { row: 0, col: 1, label: 'Extras', color: '#fecaca', article_ids: [30] },
        ],
      },
    ],
  },
} as unknown as EdgeBundleEvent

describe('buildKitchenProductSummary', () => {
  it('aggregates articles by article id with per-table breakdown', () => {
    const orders = [
      {
        id: 1,
        table_number: 5,
        lines: [
          {
            id: 1,
            line_index: 0,
            line: {
              article_id: 10,
              qty: 2,
              note: '',
              additions: [{ article_id: 30, qty: 1 }],
            },
            qty_total: 2,
            qty_printed: 0,
            qty_remaining: 2,
          },
        ],
      },
      {
        id: 2,
        table_number: 12,
        lines: [
          {
            id: 2,
            line_index: 0,
            line: { article_id: 10, qty: 1, note: '', additions: [] },
            qty_total: 1,
            qty_printed: 0,
            qty_remaining: 1,
          },
        ],
      },
    ] as unknown as KitchenOrderTicket[]

    const summary = buildKitchenProductSummary(orders, event)
    expect(summary.articles).toHaveLength(1)
    expect(summary.articles[0].totalQty).toBe(3)
    expect(summary.articles[0].name).toBe('Burger')
    expect(summary.articles[0].breakdown).toEqual([
      { label: 'Tisch 5', qty: 2 },
      { label: 'Tisch 12', qty: 1 },
    ])
    expect(summary.articles[0].color).toBe('#fef08a')
  })

  it('sorts articles alphabetically by name', () => {
    const orders = [
      {
        id: 1,
        table_number: 1,
        lines: [
          {
            id: 1,
            line_index: 0,
            line: { article_id: 10, qty: 1, note: '', additions: [] },
            qty_total: 1,
            qty_printed: 0,
            qty_remaining: 1,
          },
          {
            id: 2,
            line_index: 1,
            line: { article_id: 20, qty: 1, note: '', additions: [] },
            qty_total: 1,
            qty_printed: 0,
            qty_remaining: 1,
          },
        ],
      },
    ] as unknown as KitchenOrderTicket[]

    const summary = buildKitchenProductSummary(orders, event)
    expect(summary.articles.map((row) => row.name)).toEqual(['Bier', 'Burger'])
  })

  it('aggregates additions separately from main articles', () => {
    const orders = [
      {
        id: 1,
        table_number: 4,
        lines: [
          {
            id: 1,
            line_index: 0,
            line: {
              article_id: 10,
              qty: 2,
              note: '',
              additions: [{ article_id: 30, qty: 1, name: 'mit Salat' }],
            },
            qty_total: 2,
            qty_printed: 0,
            qty_remaining: 2,
          },
        ],
      },
      {
        id: 2,
        table_number: 22,
        lines: [
          {
            id: 2,
            line_index: 0,
            line: {
              article_id: 10,
              qty: 1,
              note: '',
              additions: [{ article_id: 30, qty: 1, name: 'mit Salat' }],
            },
            qty_total: 1,
            qty_printed: 0,
            qty_remaining: 1,
          },
        ],
      },
    ] as unknown as KitchenOrderTicket[]

    const summary = buildKitchenProductSummary(orders, event)
    expect(summary.articles).toHaveLength(1)
    expect(summary.articles[0].totalQty).toBe(3)
    expect(summary.additions).toHaveLength(1)
    expect(summary.additions[0].name).toBe('mit Salat')
    expect(summary.additions[0].totalQty).toBe(3)
    expect(summary.additions[0].breakdown).toEqual([
      { label: 'Tisch 4', qty: 2 },
      { label: 'Tisch 22', qty: 1 },
    ])
  })
})

describe('kitchenProductLocationShortLabel', () => {
  it('strips the Tisch prefix for compact table headers', () => {
    expect(kitchenProductLocationShortLabel('Tisch 48')).toBe('48')
    expect(kitchenProductLocationShortLabel('Pickup A1')).toBe('A1')
    expect(kitchenProductLocationShortLabel('Bestellung #10')).toBe('Bestellung #10')
  })
})
