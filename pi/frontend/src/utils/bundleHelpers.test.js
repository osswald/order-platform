import { describe, expect, it } from 'vitest'
import {
  cartLineLabelForEvent,
  fixedAmountVouchersForCell,
  getDefaultLayout,
  hasAdditions,
  isArticleSellable,
  lineAdditionLabels,
  lineIdentityKey,
  lineIdentityKeyFromItem,
  normalizeLineAdditions,
} from './bundleHelpers'

describe('normalizeLineAdditions', () => {
  it('drops invalid entries and enforces minimum qty', () => {
    expect(normalizeLineAdditions([null, { article_id: 2 }, { article_id: 3, qty: 0 }])).toEqual([
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
})

describe('isArticleSellable', () => {
  it('rejects additions and explicitly unsellable articles', () => {
    expect(isArticleSellable({ is_addition: true })).toBe(false)
    expect(isArticleSellable({ sellable: false })).toBe(false)
    expect(isArticleSellable({ name: 'Bier' })).toBe(true)
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
    }
    expect(lineAdditionLabels({ article_id: 1, additions: [{ article_id: 2 }] }, arts)).toEqual([
      { id: 2, name: 'Zitrone' },
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
    }
    expect(
      cartLineLabelForEvent({ kind: 'voucher_sale', voucher_definition_uuid: 'v-1' }, event),
    ).toBe('Gutschein 20')
    expect(cartLineLabelForEvent({ article_id: 10 }, event)).toBe('Bier')
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
    }
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
    }
    expect(getDefaultLayout(withDefault).uuid).toBe('b')

    const firstOnly = {
      configuration: { app_layouts: [{ uuid: 'only' }] },
    }
    expect(getDefaultLayout(firstOnly).uuid).toBe('only')
    expect(getDefaultLayout({})).toBeNull()
  })
})

describe('hasAdditions', () => {
  it('detects articles with additions', () => {
    expect(hasAdditions({ additions: [{ article_id: 1 }] })).toBe(true)
    expect(hasAdditions({ additions: [] })).toBe(false)
  })
})
