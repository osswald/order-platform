import type { ArticleRead } from '@/types/api'
import type { StationArticleTreeNode } from '@/types/ui'

export interface TreeViewNode {
  key: string
  title: string
  children?: TreeViewNode[]
}

export interface SelectedArticleGroup {
  categoryId: number
  categoryName: string
  articles: ArticleRead[]
}

/** Stable group key when category is missing from a minimal/orphaned article payload. */
const UNCATEGORIZED_CATEGORY_ID = 0

function categoryIdForArticle(art: ArticleRead): number {
  if (art.article_category_id == null || Number.isNaN(Number(art.article_category_id))) {
    return UNCATEGORIZED_CATEGORY_ID
  }
  return Number(art.article_category_id)
}

export function buildArticleCategoryTree(articles: ArticleRead[]): StationArticleTreeNode[] {
  const byCategory = new Map<number, { name: string; articles: ArticleRead[] }>()
  for (const art of articles) {
    const catId = categoryIdForArticle(art)
    const existing = byCategory.get(catId)
    if (existing) {
      existing.articles.push(art)
    } else {
      byCategory.set(catId, {
        name: art.article_category_name || '',
        articles: [art],
      })
    }
  }

  const categories = [...byCategory.entries()].sort((a, b) =>
    a[1].name.localeCompare(b[1].name, undefined, { sensitivity: 'base' }),
  )

  const nodes: StationArticleTreeNode[] = []
  for (const [catId, cat] of categories) {
    const children = [...cat.articles]
      .sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }))
      .map((art) => ({
        key: `art-${art.id}`,
        label: `${art.label} — ${art.name}`,
      }))
    if (children.length) {
      nodes.push({
        key: `cat-${catId}`,
        label: cat.name,
        children,
      })
    }
  }
  return nodes
}

export function mapTreeNodes(nodes: StationArticleTreeNode[]): TreeViewNode[] {
  return (nodes || []).map((n) => ({
    key: n.key,
    title: n.label,
    children: n.children?.length ? mapTreeNodes(n.children) : undefined,
  }))
}

export function filterTreeNodes(nodes: TreeViewNode[], query: string): TreeViewNode[] {
  const out: TreeViewNode[] = []
  for (const node of nodes) {
    if (node.children?.length) {
      const filteredChildren = filterTreeNodes(node.children, query)
      if (filteredChildren.length) {
        out.push({ ...node, children: filteredChildren })
      } else if (node.title.toLowerCase().includes(query)) {
        out.push({ ...node })
      }
    } else if (node.title.toLowerCase().includes(query)) {
      out.push({ ...node })
    }
  }
  return out
}

export function partitionArticlesBySelection(
  articles: ArticleRead[],
  selectedIds: number[],
): { available: ArticleRead[]; selected: ArticleRead[] } {
  const selectedSet = new Set(selectedIds.map(Number))
  const available: ArticleRead[] = []
  const selected: ArticleRead[] = []
  for (const art of articles) {
    if (selectedSet.has(Number(art.id))) {
      selected.push(art)
    } else {
      available.push(art)
    }
  }
  return { available, selected }
}

export function buildSelectedArticleGroups(
  articles: ArticleRead[],
  selectedIds: number[],
): SelectedArticleGroup[] {
  const selectedSet = new Set(selectedIds.map(Number))
  const byCategory = new Map<number, { name: string; articles: ArticleRead[] }>()
  for (const art of articles) {
    if (!selectedSet.has(Number(art.id))) continue
    const catId = categoryIdForArticle(art)
    const existing = byCategory.get(catId)
    if (existing) {
      existing.articles.push(art)
    } else {
      byCategory.set(catId, {
        name: art.article_category_name || '',
        articles: [art],
      })
    }
  }

  return [...byCategory.entries()]
    .sort((a, b) => a[1].name.localeCompare(b[1].name, undefined, { sensitivity: 'base' }))
    .map(([categoryId, cat]) => ({
      categoryId,
      categoryName: cat.name,
      articles: [...cat.articles].sort((a, b) =>
        (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }),
      ),
    }))
}

export function filterSelectedArticleGroups(
  groups: SelectedArticleGroup[],
  query: string,
): SelectedArticleGroup[] {
  const q = query.trim().toLowerCase()
  if (!q) return groups
  const out: SelectedArticleGroup[] = []
  for (const group of groups) {
    const categoryMatches = group.categoryName.toLowerCase().includes(q)
    const articles = group.articles.filter((art) => {
      const label = `${art.label} — ${art.name}`.toLowerCase()
      return label.includes(q) || (art.name || '').toLowerCase().includes(q)
    })
    if (categoryMatches) {
      out.push(group)
    } else if (articles.length) {
      out.push({ ...group, articles })
    }
  }
  return out
}

export function articleTreeKeyToId(key: string): number | null {
  if (!key.startsWith('art-')) return null
  const id = Number(key.replace(/^art-/, ''))
  return Number.isNaN(id) ? null : id
}
