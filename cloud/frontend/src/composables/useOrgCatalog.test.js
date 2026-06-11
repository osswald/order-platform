import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { invalidateOrgCatalog, loadOrgCatalog } from './useOrgCatalog'

vi.mock('../api', () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from '../api'

describe('useOrgCatalog', () => {
  beforeEach(() => {
    invalidateOrgCatalog(1)
    vi.mocked(apiFetch).mockReset()
  })

  afterEach(() => {
    invalidateOrgCatalog(1)
  })

  it('fetches org-scoped minimal articles and waiters', async () => {
    vi.mocked(apiFetch).mockImplementation((url) => {
      if (url.includes('/articles/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: 1, name: 'Cola', label: 'COLA', organisation_id: 1, is_addition: false }]),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([{ id: 2, name: 'Anna', pin: '1234', organisation_id: 1 }]),
      })
    })

    const result = await loadOrgCatalog(1)

    expect(apiFetch).toHaveBeenCalledWith('/articles/?minimal=true&organisation_id=1')
    expect(apiFetch).toHaveBeenCalledWith('/waiters/?organisation_id=1')
    expect(result.articles).toHaveLength(1)
    expect(result.waiters).toHaveLength(1)
    expect(result.fromCache).toBe(false)
  })

  it('returns cached catalog immediately on subsequent loads', async () => {
    vi.mocked(apiFetch).mockImplementation((url) => {
      if (url.includes('/articles/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    })

    await loadOrgCatalog(1)
    vi.mocked(apiFetch).mockClear()

    const result = await loadOrgCatalog(1)

    expect(result.fromCache).toBe(true)
    expect(result.refreshPromise).toBeTruthy()
  })
})
