import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '../api'
import { invalidateOrgCatalog, loadOrgCatalog } from './useOrgCatalog'

describe('loadOrgCatalog', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
    invalidateOrgCatalog(1)
    invalidateOrgCatalog(null)
  })

  it('loads articles and waiters for an organisation', async () => {
    vi.mocked(apiJson).mockImplementation((url) => {
      if (String(url).includes('/articles/')) {
        return Promise.resolve([{ id: 1, name: 'Beer' }])
      }
      if (String(url).includes('/waiters/')) {
        return Promise.resolve([{ id: 2, name: 'Anna' }])
      }
      return Promise.reject(new Error(`unexpected url ${url}`))
    })

    const result = await loadOrgCatalog(1)

    expect(apiJson).toHaveBeenCalledWith('/articles/?minimal=true&organisation_id=1')
    expect(apiJson).toHaveBeenCalledWith('/waiters/?organisation_id=1')
    expect(result.articles).toHaveLength(1)
    expect(result.waiters).toHaveLength(1)
    expect(result.fromCache).toBe(false)
  })

  it('returns cached catalog immediately on subsequent loads', async () => {
    vi.mocked(apiJson).mockImplementation((url) => {
      if (String(url).includes('/articles/')) {
        return Promise.resolve([{ id: 1, name: 'Beer' }])
      }
      return Promise.resolve([{ id: 2, name: 'Anna' }])
    })

    await loadOrgCatalog(1)
    vi.mocked(apiJson).mockClear()

    const result = await loadOrgCatalog(1)

    expect(result.fromCache).toBe(true)
    expect(result.refreshPromise).toBeTruthy()
  })
})
