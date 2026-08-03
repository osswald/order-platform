import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiJson } from '../api'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

describe('waiters org-scoped list fetch', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('requests organisation_id when active organisation is set', async () => {
    vi.mocked(apiJson).mockResolvedValue([])
    const activeOrganisationId = 42
    await apiJson(
      activeOrganisationId != null
        ? `/waiters/?organisation_id=${activeOrganisationId}`
        : '/waiters/',
    )
    expect(apiJson).toHaveBeenCalledWith('/waiters/?organisation_id=42')
  })

  it('falls back to tenant-wide list when no active organisation', async () => {
    vi.mocked(apiJson).mockResolvedValue([])
    const activeOrganisationId: number | null = null
    await apiJson(
      activeOrganisationId != null
        ? `/waiters/?organisation_id=${activeOrganisationId}`
        : '/waiters/',
    )
    expect(apiJson).toHaveBeenCalledWith('/waiters/')
  })
})
