import { describe, expect, it } from 'vitest'
import {
  mapLayoutsToPutPayload,
  resolveAppLayoutsForPut,
} from './eventConfigLayoutsPayload'
import type { EventLayoutLocal } from '@/types/ui'

const localLayouts: EventLayoutLocal[] = [
  {
    uuid: 'layout-1',
    name: 'Main',
    is_default: true,
    grid_width: 2,
    grid_height: 2,
    cells: [],
  },
]

const serverLayouts = [
  {
    uuid: 'layout-1',
    name: 'Main',
    is_default: true,
    grid_width: 2,
    grid_height: 2,
    cells: [
      {
        row: 0,
        col: 0,
        label: 'Beer',
        color: '#ffcc00',
        article_ids: [10],
        voucher_definition_uuid: null,
        voucher_definition_uuids: [],
      },
    ],
  },
]

describe('resolveAppLayoutsForPut', () => {
  it('uses server layout cells when local cells are not loaded yet', () => {
    const payload = resolveAppLayoutsForPut({
      layoutsLocal: localLayouts,
      layoutCellsLoaded: false,
      serverLayouts,
    })

    expect(payload).toHaveLength(1)
    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0]).toMatchObject({
      row: 0,
      col: 0,
      label: 'Beer',
      article_ids: [10],
    })
  })

  it('uses local layout cells after the layouts tab loaded them', () => {
    const loadedLocal: EventLayoutLocal[] = [
      {
        ...localLayouts[0],
        cells: [
          {
            row: 1,
            col: 1,
            label: 'Wine',
            color: '#aa0000',
            article_ids: [11],
            voucher_definition_uuid: null,
            voucher_definition_uuids: [],
          },
        ],
      },
    ]

    const payload = resolveAppLayoutsForPut({
      layoutsLocal: loadedLocal,
      layoutCellsLoaded: true,
      serverLayouts,
    })

    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0]).toMatchObject({
      row: 1,
      col: 1,
      label: 'Wine',
      article_ids: [11],
    })
  })

  it('falls back to local layouts when server has none', () => {
    const payload = resolveAppLayoutsForPut({
      layoutsLocal: localLayouts,
      layoutCellsLoaded: false,
      serverLayouts: [],
    })

    expect(payload).toHaveLength(1)
    expect(payload[0].uuid).toBe('layout-1')
    expect(payload[0].cells).toEqual([])
  })
})

describe('mapLayoutsToPutPayload', () => {
  it('drops cells outside the grid bounds', () => {
    const payload = mapLayoutsToPutPayload([
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 1,
        grid_height: 1,
        cells: [
          { row: 0, col: 0, label: 'Ok', color: '#eee', article_ids: [] },
          { row: 1, col: 0, label: 'Out', color: '#eee', article_ids: [] },
        ],
      },
    ])

    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0].label).toBe('Ok')
  })
})
