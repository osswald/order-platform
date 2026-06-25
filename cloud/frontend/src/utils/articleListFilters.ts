import type { ArticleRead } from '@/types/api'

export type ArticleListFilters = {
  search: string
  categoryId: number | null
  type: 'articles' | 'additions' | 'all'
  status: 'active' | 'inactive' | 'all'
}

export function filterArticleList(
  items: ArticleRead[],
  filters: ArticleListFilters,
  matchesSearch: (article: ArticleRead, term: string) => boolean,
): ArticleRead[] {
  const term = filters.search.trim().toLowerCase()

  return items.filter((article) => {
    if (!matchesSearch(article, term)) return false
    if (filters.categoryId != null && Number(article.article_category_id) !== Number(filters.categoryId)) {
      return false
    }
    if (filters.type === 'articles' && article.is_addition) return false
    if (filters.type === 'additions' && !article.is_addition) return false
    if (filters.status === 'active' && !article.is_active) return false
    if (filters.status === 'inactive' && article.is_active) return false
    return true
  })
}
