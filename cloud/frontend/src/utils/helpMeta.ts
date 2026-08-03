import { getHelpCategories } from '@/content/help/helpIndex'

export interface HelpArticleMeta {
  slug: string
  title: string
  summary: string
  relatedRoutes?: string[]
}

export interface HelpCategory {
  id: string
  title: string
  articles: HelpArticleMeta[]
}

export interface HelpArticle extends HelpArticleMeta {
  categoryId: string
  categoryTitle: string
  html?: string
}

function flattenArticles(): HelpArticle[] {
  const articles: HelpArticle[] = []
  for (const category of getHelpCategories()) {
    for (const article of category.articles) {
      articles.push({
        ...article,
        categoryId: category.id,
        categoryTitle: category.title,
      })
    }
  }
  return articles
}

export function getCategories(): HelpCategory[] {
  return getHelpCategories()
}

export function getAllArticles(): HelpArticle[] {
  return flattenArticles()
}

export function getArticleMeta(slug: string): HelpArticle | null {
  return flattenArticles().find((article) => article.slug === slug) ?? null
}

export function getArticlesForRoute(routeName: string): HelpArticle[] {
  if (!routeName) return []
  return flattenArticles().filter((article) => article.relatedRoutes?.includes(routeName))
}

export function getArticlesInCategory(categoryId: string): HelpArticle[] {
  const category = getHelpCategories().find((entry) => entry.id === categoryId)
  if (!category) return []

  return category.articles.map((article) => ({
    ...article,
    categoryId: category.id,
    categoryTitle: category.title,
  }))
}
