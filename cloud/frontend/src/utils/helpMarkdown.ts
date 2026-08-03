import MarkdownIt from 'markdown-it'
import { currentLocale } from '@/i18n'
import {
  getAllArticles,
  getArticleMeta,
  type HelpArticle,
} from './helpMeta'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

/** Eager within this module only — imported from Help Center / dialog, not the app shell. */
const markdownModules = import.meta.glob('../content/help/*/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

function helpLocale(): 'de' | 'en' {
  const locale = currentLocale()
  return locale === 'en' ? 'en' : 'de'
}

function markdownPathForSlug(slug: string): string {
  return `../content/help/${helpLocale()}/${slug}.md`
}

function rawMarkdownForSlug(slug: string): string | null {
  const localized = markdownModules[markdownPathForSlug(slug)]
  if (localized) return localized
  if (helpLocale() !== 'de') {
    return markdownModules[`../content/help/de/${slug}.md`] ?? null
  }
  return null
}

export function getArticle(slug: string): HelpArticle | null {
  const meta = getArticleMeta(slug)
  if (!meta) return null

  const raw = rawMarkdownForSlug(slug)
  if (!raw) return null

  return {
    ...meta,
    html: md.render(raw),
  }
}

export function searchArticles(query: string): HelpArticle[] {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return getAllArticles()

  return getAllArticles().filter((article) => {
    const raw = rawMarkdownForSlug(article.slug) ?? ''
    return (
      article.title.toLowerCase().includes(normalized) ||
      article.summary.toLowerCase().includes(normalized) ||
      raw.toLowerCase().includes(normalized)
    )
  })
}

export {
  getAllArticles,
  getArticleMeta,
  getArticlesForRoute,
  getArticlesInCategory,
  getCategories,
} from './helpMeta'
