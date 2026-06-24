import { describe, expect, it } from 'vitest'
import { getHelpCategories } from '../content/help/helpIndex.js'
import {
  getAllArticles,
  getArticle,
  getArticlesForRoute,
  searchArticles,
} from './helpArticles.js'

describe('helpArticles index consistency', () => {
  it('resolves every indexed slug to a non-empty markdown file', () => {
    for (const article of getAllArticles()) {
      const loaded = getArticle(article.slug)
      expect(loaded, `missing markdown for ${article.slug}`).not.toBeNull()
      expect(loaded?.html?.length ?? 0).toBeGreaterThan(0)
    }
  })

  it('covers every category article from helpIndex', () => {
    const indexedSlugs = getHelpCategories().flatMap((category) =>
      category.articles.map((article) => article.slug),
    )
    const loadedSlugs = getAllArticles().map((article) => article.slug)
    expect(loadedSlugs.sort()).toEqual(indexedSlugs.sort())
  })
})

describe('searchArticles', () => {
  it('returns all articles for an empty query', () => {
    expect(searchArticles('')).toHaveLength(getAllArticles().length)
    expect(searchArticles('   ')).toHaveLength(getAllArticles().length)
  })

  it('matches title and summary', () => {
    const results = searchArticles('stripe')
    expect(results.some((article) => article.slug === 'stripe-connect')).toBe(true)
  })

  it('matches markdown body text', () => {
    const results = searchArticles('Pairing-Code')
    expect(results.some((article) => article.slug === 'appliance-pairing')).toBe(true)
  })
})

describe('getArticlesForRoute', () => {
  it('returns event help for events-detail', () => {
    const results = getArticlesForRoute('events-detail')
    expect(results.map((article) => article.slug)).toContain('event-setup')
  })

  it('returns empty list for unknown routes', () => {
    expect(getArticlesForRoute('unknown-route')).toEqual([])
  })
})
