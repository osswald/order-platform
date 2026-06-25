import { describe, expect, it } from 'vitest'
import type { ArticleRead } from '@/types/api'
import { filterArticleList } from './articleListFilters'

const alwaysMatch = () => true
const neverMatch = () => false

function article(overrides: Partial<ArticleRead> & Pick<ArticleRead, 'id'>): ArticleRead {
  return {
    name: 'Item',
    label: 'ITEM',
    price: 1,
    article_category_id: 1,
    is_addition: false,
    is_active: true,
    article_category_name: 'Cat',
    organisation_id: 1,
    organisation_name: 'Org',
    organisation_currency: 'CHF',
    ...overrides,
  }
}

const sampleArticles: ArticleRead[] = [
  article({ id: 1, name: 'Beer', is_addition: false, is_active: true }),
  article({ id: 2, name: 'Wine', is_addition: false, is_active: false }),
  article({ id: 3, name: 'Ice', is_addition: true, is_active: true }),
  article({ id: 4, name: 'Lime', is_addition: true, is_active: false }),
]

describe('filterArticleList', () => {
  it('defaults to active articles only when status is active', () => {
    const result = filterArticleList(
      sampleArticles,
      { search: '', categoryId: null, type: 'all', status: 'active' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([1, 3])
  })

  it('filters inactive articles only', () => {
    const result = filterArticleList(
      sampleArticles,
      { search: '', categoryId: null, type: 'all', status: 'inactive' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([2, 4])
  })

  it('shows all statuses when status is all', () => {
    const result = filterArticleList(
      sampleArticles,
      { search: '', categoryId: null, type: 'all', status: 'all' },
      alwaysMatch,
    )

    expect(result).toHaveLength(4)
  })

  it('combines type and status filters', () => {
    const result = filterArticleList(
      sampleArticles,
      { search: '', categoryId: null, type: 'additions', status: 'active' },
      alwaysMatch,
    )

    expect(result.map((item) => item.id)).toEqual([3])
  })

  it('applies search matching via callback', () => {
    const result = filterArticleList(
      sampleArticles,
      { search: 'ignored', categoryId: null, type: 'all', status: 'all' },
      neverMatch,
    )

    expect(result).toEqual([])
  })
})
