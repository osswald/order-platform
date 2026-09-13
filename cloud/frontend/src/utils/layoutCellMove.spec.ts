import { describe, expect, it } from 'vitest'
import type { EventLayoutCellLocal, EventLayoutLocal } from '@/types/ui'
import {
  layoutCellHasEditorData,
  moveLayoutCell,
} from './layoutCellMove'

function cell(partial: Partial<EventLayoutCellLocal> & Pick<EventLayoutCellLocal, 'row' | 'col'>): EventLayoutCellLocal {
  return {
    label: '',
    color: '#eeeeee',
    article_ids: [],
    voucher_definition_uuid: null,
    voucher_definition_uuids: [],
    locked_addition_ids: [],
    ...partial,
  }
}

function layout(cells: EventLayoutCellLocal[], w = 3, h = 2): EventLayoutLocal {
  return {
    uuid: 'lo-1',
    name: 'Main',
    is_default: true,
    grid_width: w,
    grid_height: h,
    cells,
  }
}

describe('layoutCellHasEditorData', () => {
  it('is true for label, articles, vouchers, or non-default color', () => {
    expect(layoutCellHasEditorData(cell({ row: 0, col: 0, label: 'Beer' }))).toBe(true)
    expect(layoutCellHasEditorData(cell({ row: 0, col: 0, article_ids: [1] }))).toBe(true)
    expect(
      layoutCellHasEditorData(cell({ row: 0, col: 0, voucher_definition_uuids: ['v1'] })),
    ).toBe(true)
    expect(layoutCellHasEditorData(cell({ row: 0, col: 0, color: '#ff0000' }))).toBe(true)
  })

  it('is false for empty default placeholders', () => {
    expect(layoutCellHasEditorData(cell({ row: 0, col: 0 }))).toBe(false)
    expect(layoutCellHasEditorData(undefined)).toBe(false)
  })
})

describe('moveLayoutCell', () => {
  it('moves a filled cell onto an empty slot and preserves content', () => {
    const beer = cell({
      row: 0,
      col: 0,
      label: 'Beer',
      color: '#ffcc00',
      article_ids: [10],
      voucher_definition_uuids: ['v-1'],
      voucher_definition_uuid: 'v-1',
      locked_addition_ids: [20],
    })
    const lo = layout([beer])

    expect(moveLayoutCell(lo, 0, 0, 1, 2)).toBe('moved')
    expect(lo.cells).toHaveLength(1)
    expect(lo.cells[0]).toMatchObject({
      row: 1,
      col: 2,
      label: 'Beer',
      color: '#ffcc00',
      article_ids: [10],
      voucher_definition_uuids: ['v-1'],
      locked_addition_ids: [20],
    })
  })

  it('rejects drop onto an occupied slot', () => {
    const beer = cell({ row: 0, col: 0, label: 'Beer', article_ids: [10] })
    const cola = cell({ row: 0, col: 1, label: 'Cola', article_ids: [11] })
    const lo = layout([beer, cola])

    expect(moveLayoutCell(lo, 0, 0, 0, 1)).toBe('rejected')
    expect(lo.cells).toEqual([
      expect.objectContaining({ row: 0, col: 0, label: 'Beer' }),
      expect.objectContaining({ row: 0, col: 1, label: 'Cola' }),
    ])
  })

  it('rejects moving from an empty slot', () => {
    const lo = layout([cell({ row: 0, col: 1, label: 'Cola', article_ids: [11] })])
    expect(moveLayoutCell(lo, 0, 0, 1, 0)).toBe('rejected')
    expect(lo.cells[0]).toMatchObject({ row: 0, col: 1, label: 'Cola' })
  })

  it('returns noop for same slot', () => {
    const beer = cell({ row: 0, col: 0, label: 'Beer', article_ids: [10] })
    const lo = layout([beer])
    expect(moveLayoutCell(lo, 0, 0, 0, 0)).toBe('noop')
    expect(lo.cells[0]).toMatchObject({ row: 0, col: 0, label: 'Beer' })
  })

  it('rejects out-of-bounds targets', () => {
    const beer = cell({ row: 0, col: 0, label: 'Beer', article_ids: [10] })
    const lo = layout([beer], 2, 2)
    expect(moveLayoutCell(lo, 0, 0, 5, 5)).toBe('rejected')
    expect(lo.cells[0]).toMatchObject({ row: 0, col: 0 })
  })
})
