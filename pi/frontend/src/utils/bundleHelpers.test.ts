import { describe, expect, it } from 'vitest'
import type { EdgeBundleArticle, EdgeBundleEvent, EdgeBundleResponse } from '@/types/api'
import {
  articlesForIds,
  cartIngredientUsage,
  cartLineLabelForEvent,
  cellVoucherUuids,
  fixedAmountVouchersForCell,
  getDefaultLayout,
  hasAdditions,
  isArticleSellable,
  lineAdditionLabels,
  lineIdentityKey,
  lineIdentityKeyFromItem,
  maxAddQty,
  normalizeLineAdditions,
  printerHostConfigured,
  positionCommentPresets,
  positionCommentsEnabled,
  receiptPrintTargets,
  resolveStationUuidForArticle,
  voucherDefinitionByUuid,
} from './bundleHelpers'

describe('normalizeLineAdditions', () => {
  it('drops invalid entries and enforces minimum qty', () => {
    expect(
      normalizeLineAdditions(
        [null, { article_id: 2 }, { article_id: 3, qty: 0 }] as unknown as Parameters<
          typeof normalizeLineAdditions
        >[0],
      ),
    ).toEqual([
      { article_id: 2, qty: 1 },
      { article_id: 3, qty: 1 },
    ])
  })
})

describe('lineIdentityKey', () => {
  it('sorts additions for a stable key', () => {
    const a = lineIdentityKey(1, 'note', [
      { article_id: 3, qty: 1 },
      { article_id: 2, qty: 2 },
    ])
    const b = lineIdentityKey(1, 'note', [
      { article_id: 2, qty: 2 },
      { article_id: 3, qty: 1 },
    ])
    expect(a).toBe(b)
    expect(a).toBe('1:note:[{"article_id":2,"qty":2},{"article_id":3,"qty":1}]')
  })
})

describe('lineIdentityKeyFromItem', () => {
  it('includes normalized discount in the key', () => {
    const key = lineIdentityKeyFromItem({
      article_id: 5,
      note: '',
      additions: [],
      discount: { kind: 'percent', value: 150 },
    })
    expect(key).toContain('{"kind":"percent","value":100}')
  })

  it('includes amount discounts in the key', () => {
    const key = lineIdentityKeyFromItem({
      article_id: 5,
      discount: { kind: 'amount', value: 250 },
    })
    expect(key).toContain('{"kind":"amount","value":250}')
  })
})

describe('cartIngredientUsage', () => {
  it('includes base and addition ingredient consumption', () => {
    const articles = {
      10: {
        id: 10,
        ingredients: [{ ingredient_id: 1, amount: 1 }],
      },
      20: {
        id: 20,
        ingredients: [{ ingredient_id: 1, amount: 0.5 }],
      },
    } as unknown as Record<string, EdgeBundleArticle>
    const usage = cartIngredientUsage(
      [{ article_id: 10, qty: 2, additions: [{ article_id: 20, qty: 1 }] }],
      articles,
    )
    expect(usage[1]).toBe(3)
  })
})

describe('isArticleSellable', () => {
  it('rejects additions and explicitly unsellable articles', () => {
    expect(isArticleSellable({ is_addition: true } as unknown as EdgeBundleArticle)).toBe(false)
    expect(isArticleSellable({ sellable: false } as unknown as EdgeBundleArticle)).toBe(false)
    expect(isArticleSellable({ name: 'Bier' } as unknown as EdgeBundleArticle)).toBe(true)
  })
})

describe('lineAdditionLabels', () => {
  it('resolves names from base article additions and catalog', () => {
    const arts = {
      1: {
        id: 1,
        additions: [{ article_id: 2, name: 'Zitrone' }],
      },
      2: { id: 2, name: 'Zitrone Artikel' },
    } as unknown as Record<string, EdgeBundleArticle>
    expect(lineAdditionLabels({ article_id: 1, additions: [{ article_id: 2 }] }, arts)).toEqual([
      { id: 2, name: 'Zitrone' },
    ])
  })

  it('falls back to catalog article name', () => {
    const arts = {
      1: { id: 1, additions: [] },
      3: { id: 3, name: 'Oliven' },
    } as unknown as Record<string, EdgeBundleArticle>
    expect(lineAdditionLabels({ article_id: 1, additions: [{ article_id: 3 }] }, arts)).toEqual([
      { id: 3, name: 'Oliven' },
    ])
  })
})

describe('cartLineLabelForEvent', () => {
  it('labels voucher sale and article lines', () => {
    const event = {
      configuration: {
        voucher_definitions: [{ uuid: 'v-1', name: 'Gutschein 20' }],
      },
      articles: { 10: { name: 'Bier' } },
    } as unknown as EdgeBundleEvent
    expect(
      cartLineLabelForEvent({ kind: 'voucher_sale', voucher_definition_uuid: 'v-1' }, event),
    ).toBe('Gutschein 20')
    expect(cartLineLabelForEvent({ article_id: 10 }, event)).toBe('Bier')
  })

  it('uses fallbacks for unknown voucher and article', () => {
    const event = { configuration: {}, articles: {} } as unknown as EdgeBundleEvent
    expect(
      cartLineLabelForEvent({ kind: 'voucher_sale', voucher_definition_uuid: 'missing' }, event),
    ).toBe('Gutschein')
    expect(cartLineLabelForEvent({ article_id: 99 }, event)).toBe('Artikel #99')
  })
})

describe('fixedAmountVouchersForCell', () => {
  it('returns fixed_amount definitions referenced by the cell', () => {
    const event = {
      configuration: {
        voucher_definitions: [
          { uuid: 'v-1', kind: 'fixed_amount', name: 'A' },
          { uuid: 'v-2', kind: 'percent', name: 'B' },
        ],
      },
    } as unknown as EdgeBundleEvent
    const cell = { voucher_definition_uuids: ['v-1', 'v-2'] }
    expect(fixedAmountVouchersForCell(event, cell)).toEqual([
      { uuid: 'v-1', kind: 'fixed_amount', name: 'A' },
    ])
  })
})

describe('getDefaultLayout', () => {
  it('prefers is_default and falls back to first layout', () => {
    const withDefault = {
      configuration: {
        app_layouts: [
          { uuid: 'a', is_default: false },
          { uuid: 'b', is_default: true },
        ],
      },
    } as unknown as EdgeBundleEvent
    expect(getDefaultLayout(withDefault)!.uuid).toBe('b')

    const firstOnly = {
      configuration: { app_layouts: [{ uuid: 'only' }] },
    } as unknown as EdgeBundleEvent
    expect(getDefaultLayout(firstOnly)!.uuid).toBe('only')
    expect(getDefaultLayout({} as unknown as EdgeBundleEvent)).toBeNull()
  })
})

describe('hasAdditions', () => {
  it('detects articles with additions', () => {
    expect(hasAdditions({ additions: [{ article_id: 1 }] } as unknown as EdgeBundleArticle)).toBe(true)
    expect(hasAdditions({ additions: [] } as unknown as EdgeBundleArticle)).toBe(false)
  })
})

describe('maxAddQty', () => {
  it('returns remaining stock or null when not monitored', () => {
    expect(maxAddQty({ monitor_stock: true, in_stock: 5 } as unknown as EdgeBundleArticle, 2)).toBe(3)
    expect(maxAddQty({ name: 'Open' } as unknown as EdgeBundleArticle)).toBeNull()
  })
})

describe('resolveStationUuidForArticle', () => {
  it('finds the station containing the article', () => {
    const event = {
      configuration: {
        stations: [
          { uuid: 'st-a', article_ids: [10] },
          { uuid: 'st-b', article_ids: [11] },
        ],
      },
    } as unknown as EdgeBundleEvent
    expect(resolveStationUuidForArticle(event, 11)).toBe('st-b')
    expect(resolveStationUuidForArticle(event, 99)).toBeNull()
    expect(resolveStationUuidForArticle({} as unknown as EdgeBundleEvent, 10)).toBeNull()
  })
})

describe('cellVoucherUuids', () => {
  it('reads plural list and legacy single uuid', () => {
    expect(cellVoucherUuids({ voucher_definition_uuids: [' a ', ''] })).toEqual(['a'])
    expect(cellVoucherUuids({ voucher_definition_uuid: 'legacy-1' })).toEqual(['legacy-1'])
    expect(cellVoucherUuids({})).toEqual([])
  })
})

describe('voucherDefinitionByUuid', () => {
  it('finds voucher definitions on the event', () => {
    const event = {
      configuration: { voucher_definitions: [{ uuid: 'v-1', name: 'A' }] },
    } as unknown as EdgeBundleEvent
    expect(voucherDefinitionByUuid(event, 'v-1')?.name).toBe('A')
    expect(voucherDefinitionByUuid(event, 'missing')).toBeNull()
  })
})

describe('articlesForIds', () => {
  it('returns only sellable articles', () => {
    const event = {
      articles: {
        1: { id: 1, name: 'Bier' },
        2: { id: 2, name: 'Zitrone', is_addition: true },
        3: { id: 3, name: 'Wein', sellable: false },
      },
    } as unknown as EdgeBundleEvent
    expect(articlesForIds(event, [1, 2, 3])).toEqual([{ id: 1, name: 'Bier' }])
  })
})

describe('printerHostConfigured', () => {
  const event = {
    printer_hosts: {
      'st-1': '192.168.1.10:9100',
      'st-empty': ':9100',
      'reg-1': { host: 'printer.local' },
      'reg-empty': { host: '  ' },
    },
  } as unknown as EdgeBundleEvent

  it('detects configured string and object hosts', () => {
    expect(printerHostConfigured(event, 'st-1')).toBe(true)
    expect(printerHostConfigured(event, 'st-empty')).toBe(false)
    expect(printerHostConfigured(event, 'reg-1')).toBe(true)
    expect(printerHostConfigured(event, 'reg-empty')).toBe(false)
    expect(printerHostConfigured(event, 'missing')).toBe(false)
  })
})

describe('receiptPrintTargets', () => {
  it('lists configured stations and registers sorted by label', () => {
    const event = {
      printer_hosts: {
        'st-bar': '10.0.0.1:9100',
        'reg-1': '10.0.0.2:9100',
      },
      configuration: {
        stations: [{ uuid: 'st-bar', name: 'Bar' }],
        cash_registers: [{ uuid: 'reg-1', name: 'Front' }],
      },
    } as unknown as EdgeBundleEvent
    expect(receiptPrintTargets(event)).toEqual([
      { uuid: 'st-bar', label: 'Bar', kind: 'station' },
      { uuid: 'reg-1', label: 'Kasse: Front', kind: 'register' },
    ])
  })
})

describe('positionComments bundle helpers', () => {
  it('reads org-level comment flag and presets', () => {
    const bundle = {
      position_comments_enabled: true,
      position_comment_presets: [{ id: 1, text: 'medium' }],
    } as unknown as EdgeBundleResponse
    expect(positionCommentsEnabled(bundle)).toBe(true)
    expect(positionCommentPresets(bundle)).toEqual([{ id: 1, text: 'medium' }])
    expect(positionCommentsEnabled({} as unknown as EdgeBundleResponse)).toBe(false)
    expect(positionCommentPresets(null)).toEqual([])
  })
})
