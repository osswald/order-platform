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
  fetchSumupReaderTelemetry,
  pairSumupReader,
  putSumupOrganisationApiKey,
  renameSumupReader,
  unpairSumupReader,
} from './sumupCloud'

describe('sumupCloud', () => {
  beforeEach(() => {
    vi.mocked(apiJson).mockReset()
  })

  it('fetchSumupOrganisationStatus returns connected status with payments_ready', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      organisation_id: 1,
      connected: true,
      merchant_code: 'MC123',
      merchant_name: 'Sandbox Cafe',
      merchant_sandbox: true,
      merchant_country: 'CH',
      reader_count: 2,
      payments_ready: true,
    })
    await expect(fetchSumupOrganisationStatus(1)).resolves.toEqual({
      configured: true,
      organisation_id: 1,
      connected: true,
      merchant_code: 'MC123',
      merchant_name: 'Sandbox Cafe',
      merchant_sandbox: true,
      merchant_country: 'CH',
      reader_count: 2,
      payments_ready: true,
    })
  })

  it('maps 503 status to configured:false', async () => {
    vi.mocked(apiJson).mockRejectedValue(createApiError('unavailable', 503))
    await expect(fetchSumupOrganisationStatus(1)).resolves.toEqual({
      configured: false,
      error: 'sumupDevices.notConfigured',
    })
  })

  it('putSumupOrganisationApiKey sends API key body', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      organisation_id: 1,
      connected: true,
      merchant_code: 'MC123',
      merchant_name: null,
      merchant_sandbox: false,
      merchant_country: null,
      reader_count: 0,
      payments_ready: false,
    })
    await putSumupOrganisationApiKey(1, 'sup_sk_test')
    expect(apiJson).toHaveBeenCalledWith('/sumup/organisations/1/api-key', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: 'sup_sk_test' }),
    })
  })

  it('putSumupOrganisationApiKey includes merchant_code when provided', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      organisation_id: 1,
      connected: true,
      merchant_code: 'MCSAND',
      merchant_name: 'Testfirma',
      merchant_sandbox: true,
      merchant_country: 'CH',
      reader_count: 0,
      payments_ready: true,
    })
    await putSumupOrganisationApiKey(1, 'sup_sk_test', 'MCSAND')
    expect(apiJson).toHaveBeenCalledWith('/sumup/organisations/1/api-key', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: 'sup_sk_test', merchant_code: 'MCSAND' }),
    })
  })

  it('putSumupOrganisationApiKey maps multi-merchant 409 to selection error', async () => {
    vi.mocked(apiJson).mockRejectedValue(
      createApiError('choose merchant', 409, {
        code: 'sumup_merchant_selection_required',
        message: 'choose merchant',
        merchants: [
          { merchant_code: 'MCLIVE', merchant_name: 'Live', sandbox: false, country: 'CH' },
          { merchant_code: 'MCSAND', merchant_name: 'Sandbox', sandbox: true, country: 'CH' },
        ],
      }),
    )
    await expect(putSumupOrganisationApiKey(1, 'sup_sk_multi')).rejects.toMatchObject({
      name: 'SumupMerchantSelectionRequiredError',
      merchants: [
        { merchant_code: 'MCLIVE', merchant_name: 'Live', sandbox: false, country: 'CH' },
        { merchant_code: 'MCSAND', merchant_name: 'Sandbox', sandbox: true, country: 'CH' },
      ],
    })
  })

  it('authorizeSumupOrganisation rethrows 503 with cause (dormant OAuth helper)', async () => {
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

  it('fetchSumupReaderTelemetry calls the telemetry path', async () => {
    vi.mocked(apiJson).mockResolvedValueOnce({
      id: 5,
      sumup_reader_id: 'r1',
      label: 'Bar',
      device_identifier: 'U1DT3NA00-CN',
      device_model: 'solo',
      telemetry_available: true,
      online_status: 'ONLINE',
      battery_level: 80,
      connection_type: 'Wi-Fi',
      firmware_version: '3.3.3.21',
      last_activity: '2025-09-25T15:20:00Z',
      state: 'IDLE',
    })
    await expect(fetchSumupReaderTelemetry(3, 5)).resolves.toMatchObject({
      telemetry_available: true,
      device_identifier: 'U1DT3NA00-CN',
      online_status: 'ONLINE',
    })
    expect(apiJson).toHaveBeenCalledWith('/sumup/organisations/3/readers/5/telemetry')
  })
})
