import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api', () => ({
  apiJson: vi.fn(),
}))

vi.mock('../i18n', () => ({
  i18n: {
    global: {
      t: (key: string) => key,
    },
  },
}))

import { apiJson } from '../api'
import { createApiError } from '../api/auth'
import {
  authorizeSumupOrganisation,
  disconnectSumupOrganisation,
  fetchSumupOrganisationStatus,
  fetchSumupReaders,
  pairSumupReader,
  renameSumupReader,
  unpairSumupReader,
} from './sumupCloud'

describe('sumupCloud', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('fetchSumupOrganisationStatus returns connected status', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      organisation_id: 1,
      connected: true,
      merchant_code: 'MC123',
      reader_count: 2,
    })
    await expect(fetchSumupOrganisationStatus(1)).resolves.toEqual({
      configured: true,
      organisation_id: 1,
      connected: true,
      merchant_code: 'MC123',
      reader_count: 2,
    })
  })

  it('maps 503 status to configured:false', async () => {
    vi.mocked(apiJson).mockRejectedValue(createApiError('unavailable', 503))
    await expect(fetchSumupOrganisationStatus(1)).resolves.toEqual({
      configured: false,
      error: 'sumupDevices.notConfigured',
    })
  })

  it('authorizeSumupOrganisation rethrows 503 with cause', async () => {
    const apiErr = createApiError('unavailable', 503)
    vi.mocked(apiJson).mockRejectedValue(apiErr)
    await expect(authorizeSumupOrganisation(1)).rejects.toMatchObject({
      message: 'sumupDevices.notConfigured',
      cause: apiErr,
    })
  })

  it('calls reader management endpoints with expected paths', async () => {
    vi.mocked(apiJson).mockResolvedValueOnce([{ id: 5, sumup_reader_id: 'r1', label: 'Bar', status: 'paired' }])
    await expect(fetchSumupReaders(3)).resolves.toEqual([
      { id: 5, sumup_reader_id: 'r1', label: 'Bar', status: 'paired' },
    ])
    expect(apiJson).toHaveBeenCalledWith('/sumup/organisations/3/readers')

    vi.mocked(apiJson).mockResolvedValueOnce({ id: 6, sumup_reader_id: 'r2', label: 'Terra', status: 'paired' })
    await pairSumupReader(3, { pairing_code: 'ABC', label: 'Terra' })
    expect(apiJson).toHaveBeenLastCalledWith('/sumup/organisations/3/readers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pairing_code: 'ABC', label: 'Terra' }),
    })

    vi.mocked(apiJson).mockResolvedValueOnce({ id: 6, sumup_reader_id: 'r2', label: 'Terrasse', status: 'paired' })
    await renameSumupReader(3, 6, 'Terrasse')
    expect(apiJson).toHaveBeenLastCalledWith('/sumup/organisations/3/readers/6', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label: 'Terrasse' }),
    })

    vi.mocked(apiJson).mockResolvedValueOnce(undefined)
    await unpairSumupReader(3, 6)
    expect(apiJson).toHaveBeenLastCalledWith('/sumup/organisations/3/readers/6', {
      method: 'DELETE',
    })

    vi.mocked(apiJson).mockResolvedValueOnce(undefined)
    await disconnectSumupOrganisation(3)
    expect(apiJson).toHaveBeenLastCalledWith('/sumup/organisations/3/disconnect', {
      method: 'POST',
    })
  })
})
