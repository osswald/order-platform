import { apiJson } from '../api'
import { i18n } from '../i18n'
import { isApiError } from '@/types/api'

function t(key: string): string {
  return i18n.global.t(key)
}

export interface SumupOrganisationStatus {
  organisation_id: number
  connected: boolean
  merchant_code: string | null
  reader_count: number
}

export type SumupOrganisationStatusView =
  | ({ configured: true } & SumupOrganisationStatus)
  | { configured: false; error: string }

export interface SumupAuthorizeResponse {
  authorize_url: string
  state: string
}

export interface SumupReader {
  id: number
  sumup_reader_id: string
  label: string
  status: string
}

export interface SumupPairReaderPayload {
  pairing_code: string
  label: string
}

async function withNotConfigured<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn()
  } catch (err: unknown) {
    if (isApiError(err) && err.status === 503) {
      throw new Error(t('sumupDevices.notConfigured'), { cause: err })
    }
    throw err
  }
}

export async function fetchSumupOrganisationStatus(
  organisationId: number | string,
): Promise<SumupOrganisationStatusView> {
  try {
    const data = await apiJson<SumupOrganisationStatus>(
      `/sumup/organisations/${organisationId}/status`,
    )
    return { configured: true, ...data }
  } catch (err: unknown) {
    if (isApiError(err) && err.status === 503) {
      return { configured: false, error: t('sumupDevices.notConfigured') }
    }
    throw err
  }
}

export async function authorizeSumupOrganisation(
  organisationId: number | string,
): Promise<SumupAuthorizeResponse> {
  return withNotConfigured(() =>
    apiJson<SumupAuthorizeResponse>(`/sumup/organisations/${organisationId}/authorize`, {
      method: 'POST',
    }),
  )
}

export async function disconnectSumupOrganisation(
  organisationId: number | string,
): Promise<void> {
  await withNotConfigured(() =>
    apiJson<void>(`/sumup/organisations/${organisationId}/disconnect`, {
      method: 'POST',
    }),
  )
}

export async function fetchSumupReaders(
  organisationId: number | string,
): Promise<SumupReader[]> {
  return withNotConfigured(() =>
    apiJson<SumupReader[]>(`/sumup/organisations/${organisationId}/readers`),
  )
}

export async function pairSumupReader(
  organisationId: number | string,
  payload: SumupPairReaderPayload,
): Promise<SumupReader> {
  return withNotConfigured(() =>
    apiJson<SumupReader>(`/sumup/organisations/${organisationId}/readers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
}

export async function renameSumupReader(
  organisationId: number | string,
  readerId: number | string,
  label: string,
): Promise<SumupReader> {
  return withNotConfigured(() =>
    apiJson<SumupReader>(`/sumup/organisations/${organisationId}/readers/${readerId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label }),
    }),
  )
}

export async function unpairSumupReader(
  organisationId: number | string,
  readerId: number | string,
): Promise<void> {
  await withNotConfigured(() =>
    apiJson<void>(`/sumup/organisations/${organisationId}/readers/${readerId}`, {
      method: 'DELETE',
    }),
  )
}
