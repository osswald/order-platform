import MarkdownIt from 'markdown-it'
import { helpCategories } from '../content/help/helpIndex.js'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const markdownModules = import.meta.glob('../content/help/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
})

function markdownPathForSlug(slug) {
  return `../content/help/${slug}.md`
}

function rawMarkdownForSlug(slug) {
  return markdownModules[markdownPathForSlug(slug)] ?? null
}

function flattenArticles() {
  const articles = []
  for (const category of helpCategories) {
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

export function getCategories() {
  return helpCategories
}

export function getAllArticles() {
  return flattenArticles()
}

export function getArticle(slug) {
  const meta = flattenArticles().find((article) => article.slug === slug)
  if (!meta) return null

  const raw = rawMarkdownForSlug(slug)
  if (!raw) return null

  return {
    ...meta,
    html: md.render(raw),
  }
}

export function searchArticles(query) {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return flattenArticles()

  return flattenArticles().filter((article) => {
    const raw = rawMarkdownForSlug(article.slug) ?? ''
    return (
      article.title.toLowerCase().includes(normalized) ||
      article.summary.toLowerCase().includes(normalized) ||
      raw.toLowerCase().includes(normalized)
    )
  })
}

export function getArticlesForRoute(routeName) {
  if (!routeName) return []
  return flattenArticles().filter((article) => article.relatedRoutes?.includes(routeName))
}

export function getArticlesInCategory(categoryId) {
  const category = helpCategories.find((entry) => entry.id === categoryId)
  if (!category) return []

  return category.articles.map((article) => ({
    ...article,
    categoryId: category.id,
    categoryTitle: category.title,
  }))
}
