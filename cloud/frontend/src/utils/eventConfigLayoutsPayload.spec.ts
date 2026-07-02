import { describe, expect, it } from 'vitest'
import {
  layoutCellHasContent,
  mapLayoutsToPutPayload,
  mergeLayoutsWithServerCells,
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

describe('mergeLayoutsWithServerCells', () => {
  it('keeps server cells for layouts that already exist', () => {
    const merged = mergeLayoutsWithServerCells(localLayouts, serverLayouts)
    expect(merged[0].cells).toHaveLength(1)
    expect(merged[0].cells?.[0].label).toBe('Beer')
  })

  it('keeps local-only layouts such as newly added ones', () => {
    const merged = mergeLayoutsWithServerCells(
      [
        ...localLayouts,
        {
          uuid: 'layout-new',
          name: 'Register 2',
          is_default: false,
          grid_width: 4,
          grid_height: 4,
          cells: [],
        },
      ],
      serverLayouts,
    )

    expect(merged).toHaveLength(2)
    expect(merged[1].uuid).toBe('layout-new')
    expect(merged[1].cells).toEqual([])
  })
})

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

  it('preserves newly added local layouts before cells are loaded', () => {
    const payload = resolveAppLayoutsForPut({
      layoutsLocal: [
        ...localLayouts,
        {
          uuid: 'layout-new',
          name: 'Register 2',
          is_default: false,
          grid_width: 4,
          grid_height: 4,
          cells: [],
        },
      ],
      layoutCellsLoaded: false,
      serverLayouts,
    })

    expect(payload).toHaveLength(2)
    expect(payload[1].uuid).toBe('layout-new')
    expect(payload[1].cells).toEqual([])
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

describe('layoutCellHasContent', () => {
  it('returns true when cell has articles', () => {
    expect(layoutCellHasContent({ row: 0, col: 0, article_ids: [1] })).toBe(true)
  })

  it('returns true when cell has voucher_definition_uuids', () => {
    expect(
      layoutCellHasContent({
        row: 0,
        col: 0,
        voucher_definition_uuids: ['v-1'],
      }),
    ).toBe(true)
  })

  it('returns true when cell has legacy voucher_definition_uuid', () => {
    expect(
      layoutCellHasContent({
        row: 0,
        col: 0,
        voucher_definition_uuid: 'v-1',
      }),
    ).toBe(true)
  })

  it('returns false for label-only cells', () => {
    expect(layoutCellHasContent({ row: 0, col: 0, label: 'Beer', article_ids: [] })).toBe(false)
  })

  it('returns false for empty cells', () => {
    expect(layoutCellHasContent({ row: 0, col: 0, label: '', article_ids: [] })).toBe(false)
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
          { row: 0, col: 0, label: 'Ok', color: '#eee', article_ids: [10] },
          { row: 1, col: 0, label: 'Out', color: '#eee', article_ids: [11] },
        ],
      },
    ])

    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0].label).toBe('Ok')
  })

  it('omits cells with no articles or vouchers', () => {
    const payload = mapLayoutsToPutPayload([
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
          {
            row: 0,
            col: 1,
            label: '',
            color: '#eeeeee',
            article_ids: [],
            voucher_definition_uuid: null,
            voucher_definition_uuids: [],
          },
        ],
      },
    ])

    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0]).toMatchObject({ row: 0, col: 0, article_ids: [10] })
  })
})
