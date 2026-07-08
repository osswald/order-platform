import { describe, expect, it } from 'vitest'
import type { ArticleRead } from '@/types/api'
import {
  articleTreeKeyToId,
  buildArticleCategoryTree,
  buildSelectedArticleGroups,
  filterSelectedArticleGroups,
  filterTreeNodes,
  mapTreeNodes,
  partitionArticlesBySelection,
} from './articleCategoryTree'

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
  article({
    id: 10,
    name: 'Bratwurst',
    label: 'BW',
    article_category_id: 1,
    article_category_name: 'Food',
  }),
  article({
    id: 11,
    name: 'Bier',
    label: 'BI',
    article_category_id: 2,
    article_category_name: 'Drinks',
  }),
  article({
    id: 12,
    name: 'Apfelwein',
    label: 'AW',
    article_category_id: 2,
    article_category_name: 'Drinks',
  }),
]

describe('buildArticleCategoryTree', () => {
  it('groups articles by category with sorted labels', () => {
    const tree = buildArticleCategoryTree(sampleArticles)
    expect(tree).toHaveLength(2)
    expect(tree[0].key).toBe('cat-2')
    expect(tree[0].label).toBe('Drinks')
    expect(tree[0].children?.map((c) => c.key)).toEqual(['art-12', 'art-11'])
    expect(tree[0].children?.[0].label).toBe('AW — Apfelwein')
    expect(tree[1].key).toBe('cat-1')
    expect(tree[1].children?.map((c) => c.key)).toEqual(['art-10'])
  })

  it('returns empty array for no articles', () => {
    expect(buildArticleCategoryTree([])).toEqual([])
  })
})

describe('mapTreeNodes and filterTreeNodes', () => {
  const tree = buildArticleCategoryTree(sampleArticles)
  const mapped = mapTreeNodes(tree)

  it('maps label to title', () => {
    expect(mapped[0].title).toBe('Drinks')
    expect(mapped[0].children?.[0].title).toBe('AW — Apfelwein')
  })

  it('filters leaves and keeps parent categories when child matches', () => {
    const filtered = filterTreeNodes(mapped, 'bier')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].title).toBe('Drinks')
    expect(filtered[0].children).toHaveLength(1)
    expect(filtered[0].children?.[0].title).toBe('BI — Bier')
  })

  it('keeps category when category name matches', () => {
    const filtered = filterTreeNodes(mapped, 'food')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].title).toBe('Food')
  })
})

describe('partitionArticlesBySelection', () => {
  it('splits available and selected articles', () => {
    const { available, selected } = partitionArticlesBySelection(sampleArticles, [10, 11])
    expect(available.map((a) => a.id)).toEqual([12])
    expect(selected.map((a) => a.id)).toEqual([10, 11])
  })
})

describe('buildSelectedArticleGroups', () => {
  it('groups selected articles by category sorted by name', () => {
    const groups = buildSelectedArticleGroups(sampleArticles, [10, 11, 12])
    expect(groups).toHaveLength(2)
    expect(groups[0].categoryName).toBe('Drinks')
    expect(groups[0].articles.map((a) => a.id)).toEqual([12, 11])
    expect(groups[1].categoryName).toBe('Food')
    expect(groups[1].articles.map((a) => a.id)).toEqual([10])
  })

  it('returns empty array when nothing selected', () => {
    expect(buildSelectedArticleGroups(sampleArticles, [])).toEqual([])
  })
})

describe('filterSelectedArticleGroups', () => {
  const groups = buildSelectedArticleGroups(sampleArticles, [10, 11, 12])

  it('filters articles by label and keeps category when name matches', () => {
    const filtered = filterSelectedArticleGroups(groups, 'bier')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].categoryName).toBe('Drinks')
    expect(filtered[0].articles.map((a) => a.id)).toEqual([11])
  })

  it('returns all articles in category when category name matches', () => {
    const filtered = filterSelectedArticleGroups(groups, 'drinks')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].articles.map((a) => a.id)).toEqual([12, 11])
  })
})

describe('articleTreeKeyToId', () => {
  it('parses art- keys', () => {
    expect(articleTreeKeyToId('art-42')).toBe(42)
  })

  it('returns null for non-article keys', () => {
    expect(articleTreeKeyToId('cat-1')).toBeNull()
  })
})
