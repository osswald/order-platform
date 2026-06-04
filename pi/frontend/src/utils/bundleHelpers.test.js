import { describe, expect, it } from 'vitest'
import {
  getDefaultLayout,
  hasAdditions,
  isArticleSellable,
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
