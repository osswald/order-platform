import { describe, expect, it } from 'vitest'
import { readLegacyOrganisationQuery, resolveContextReloadPath } from './contextReload'

describe('resolveContextReloadPath', () => {
  it('keeps list routes unchanged', () => {
    expect(resolveContextReloadPath('dashboard', '/dashboard')).toBe('/dashboard')
    expect(resolveContextReloadPath('events', '/events')).toBe('/events')
  })

  it('redirects detail routes to parent list', () => {
    expect(resolveContextReloadPath('events-detail', '/events/42')).toBe('/events')
    expect(resolveContextReloadPath('articles-detail', '/articles/7')).toBe('/articles')
  })

  it('redirects new routes to parent list', () => {
    expect(resolveContextReloadPath('events-new', '/events/new')).toBe('/events')
    expect(resolveContextReloadPath('organisations-new', '/organisations/new')).toBe('/organisations')
  })

  it('strips query string from path', () => {
    expect(resolveContextReloadPath('events', '/events?organisation=2')).toBe('/events')
  })
})

describe('readLegacyOrganisationQuery', () => {
  it('returns parsed id from organisation query', () => {
    expect(readLegacyOrganisationQuery({ organisation: '3' })).toBe(3)
  })

  it('returns null when absent or invalid', () => {
    expect(readLegacyOrganisationQuery({})).toBeNull()
    expect(readLegacyOrganisationQuery({ organisation: '' })).toBeNull()
    expect(readLegacyOrganisationQuery({ organisation: 'abc' })).toBeNull()
  })
})
