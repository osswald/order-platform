import { describe, expect, it } from 'vitest'
import type { EdgeBundleArticle, LineSelection } from '@/types/api'
import {
  asArticleLineSelection,
  isArticleLineSelection,
  voucherRedeemSelectionLabel,
} from './voucherRedeemSelection'

describe('isArticleLineSelection', () => {
  it('accepts selections with a numeric article_id', () => {
    const sel = { kind: 'article', article_id: 7, note: '', qty: 1 } as LineSelection
    expect(isArticleLineSelection(sel)).toBe(true)
  })

  it('rejects voucher sales and missing article ids', () => {
    expect(
      isArticleLineSelection({
        kind: 'voucher_sale',
        article_id: null,
        voucher_definition_uuid: 'vd-1',
        note: '',
        qty: 1,
      } as LineSelection),
    ).toBe(false)
    expect(
      isArticleLineSelection({
        kind: 'article',
        note: '',
        qty: 1,
      } as LineSelection),
    ).toBe(false)
  })
})

describe('asArticleLineSelection', () => {
  it('narrows article_id to number', () => {
    const sel = { kind: 'article', article_id: 3, note: 'x', qty: 2 } as LineSelection
    expect(asArticleLineSelection(sel)).toEqual({
      kind: 'article',
      article_id: 3,
      note: 'x',
      qty: 2,
    })
  })

  it('returns null for non-article lines', () => {
    expect(
      asArticleLineSelection({
        kind: 'voucher_sale',
        article_id: null,
        note: '',
        qty: 1,
      } as LineSelection),
    ).toBeNull()
  })
})

describe('voucherRedeemSelectionLabel', () => {
  const arts = {
    1: { id: 1, name: 'Bier', additions: [{ article_id: 2, name: 'Zitrone' }] },
    2: { id: 2, name: 'Zitrone' },
  } as unknown as Record<string, EdgeBundleArticle>

  it('uses article name and addition labels', () => {
    expect(
      voucherRedeemSelectionLabel(
        { article_id: 1, additions: [{ article_id: 2, qty: 1 }] },
        arts,
      ),
    ).toBe('Bier (+ Zitrone)')
  })

  it('falls back to article id when name is missing', () => {
    expect(voucherRedeemSelectionLabel({ article_id: 9 }, {})).toBe('Artikel #9')
  })
})
