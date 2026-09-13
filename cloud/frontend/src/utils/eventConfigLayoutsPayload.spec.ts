import { describe, expect, it } from 'vitest'
import {
  cellCanHaveLockedAdditions,
  layoutCellHasContent,
  mapLayoutsToPutPayload,
  mergeLayoutsWithServerCells,
  normalizeLockedAdditionIds,
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
        locked_addition_ids: [],
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
            locked_addition_ids: [],
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

  it('prunes layout cell articles that are no longer on any station', () => {
    const payload = resolveAppLayoutsForPut({
      layoutsLocal: localLayouts,
      layoutCellsLoaded: false,
      serverLayouts,
      stations: [{ article_ids: [] }],
    })

    expect(payload[0].cells).toEqual([])
  })

  it('keeps only layout cell articles still assigned to a station', () => {
    const payload = resolveAppLayoutsForPut({
      layoutsLocal: localLayouts,
      layoutCellsLoaded: false,
      serverLayouts: [
        {
          uuid: 'layout-1',
          cells: [
            {
              row: 0,
              col: 0,
              label: 'Mix',
              color: '#ffcc00',
              article_ids: [10, 11],
              voucher_definition_uuid: null,
              voucher_definition_uuids: [],
              locked_addition_ids: [],
            },
          ],
        },
      ],
      stations: [{ article_ids: [10] }],
    })

    expect(payload[0].cells).toHaveLength(1)
    expect(payload[0].cells?.[0].article_ids).toEqual([10])
  })
})

describe('cellCanHaveLockedAdditions', () => {
  it('returns true for exactly one article and no vouchers', () => {
    expect(cellCanHaveLockedAdditions([10], [])).toBe(true)
  })

  it('returns false for zero articles', () => {
    expect(cellCanHaveLockedAdditions([], [])).toBe(false)
  })

  it('returns false for two or more articles', () => {
    expect(cellCanHaveLockedAdditions([10, 11], [])).toBe(false)
  })

  it('returns false when any voucher is present', () => {
    expect(cellCanHaveLockedAdditions([10], ['v-1'])).toBe(false)
  })
})

describe('normalizeLockedAdditionIds', () => {
  it('keeps locked ids when the cell can have locked additions', () => {
    expect(normalizeLockedAdditionIds([10], [], [20, 21])).toEqual([20, 21])
  })

  it('clears locked ids when a second article is selected', () => {
    expect(normalizeLockedAdditionIds([10, 11], [], [20])).toEqual([])
  })

  it('clears locked ids when a voucher is selected', () => {
    expect(normalizeLockedAdditionIds([10], ['v-1'], [20])).toEqual([])
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

  it('includes locked_addition_ids on cells (default [])', () => {
    const payload = mapLayoutsToPutPayload([
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 2,
        grid_height: 1,
        cells: [
          {
            row: 0,
            col: 0,
            label: 'Combo',
            color: '#ffcc00',
            article_ids: [10],
            voucher_definition_uuids: [],
            locked_addition_ids: [20, 21],
          },
          {
            row: 0,
            col: 1,
            label: 'Plain',
            color: '#eeeeee',
            article_ids: [11],
            voucher_definition_uuids: [],
          },
        ],
      },
    ])

    expect(payload[0].cells?.[0]).toMatchObject({
      article_ids: [10],
      locked_addition_ids: [20, 21],
    })
    expect(payload[0].cells?.[1]).toMatchObject({
      article_ids: [11],
      locked_addition_ids: [],
    })
  })

  it('clears locked_addition_ids when cell has multiple articles or vouchers', () => {
    const payload = mapLayoutsToPutPayload([
      {
        uuid: 'layout-1',
        name: 'Main',
        is_default: true,
        grid_width: 2,
        grid_height: 1,
        cells: [
          {
            row: 0,
            col: 0,
            label: 'Multi',
            color: '#ffcc00',
            article_ids: [10, 11],
            voucher_definition_uuids: [],
            locked_addition_ids: [20],
          },
          {
            row: 0,
            col: 1,
            label: 'Voucher',
            color: '#eeeeee',
            article_ids: [10],
            voucher_definition_uuids: ['v-1'],
            locked_addition_ids: [20],
          },
        ],
      },
    ])

    expect(payload[0].cells?.[0]?.locked_addition_ids).toEqual([])
    expect(payload[0].cells?.[1]?.locked_addition_ids).toEqual([])
  })
})
