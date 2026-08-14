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
  merchant_name: string | null
  merchant_sandbox: boolean | null
  merchant_country: string | null
  reader_count: number
  payments_ready: boolean
}

export type SumupOrganisationStatusView =
  | ({ configured: true } & SumupOrganisationStatus)
  | { configured: false; error: string }

/** @deprecated OAuth connect is dormant; kept for reactivation when SumUp grants payments scope. */
export interface SumupAuthorizeResponse {
  authorize_url: string
  state: string
}

export interface SumupReader {
  id: number
  sumup_reader_id: string
  label: string
  status: string
  device_identifier?: string | null
  device_model?: string | null
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

export interface SumupMerchantChoice {
  merchant_code: string
  merchant_name: string | null
  sandbox: boolean | null
  country: string | null
}

export class SumupMerchantSelectionRequiredError extends Error {
  readonly merchants: SumupMerchantChoice[]
  readonly status = 409

  constructor(merchants: SumupMerchantChoice[], message: string) {
    super(message)
    this.name = 'SumupMerchantSelectionRequiredError'
    this.merchants = merchants
  }
}

function parseMerchantSelectionError(err: unknown): SumupMerchantSelectionRequiredError | null {
  if (!isApiError(err) || err.status !== 409) return null
  const detail = err.detail
  if (!detail || typeof detail !== 'object') return null
  const code = (detail as { code?: unknown }).code
  const merchants = (detail as { merchants?: unknown }).merchants
  if (code !== 'sumup_merchant_selection_required' || !Array.isArray(merchants)) return null
  const parsed: SumupMerchantChoice[] = merchants
    .filter((m): m is Record<string, unknown> => !!m && typeof m === 'object')
    .map((m) => ({
      merchant_code: String(m.merchant_code ?? ''),
      merchant_name: typeof m.merchant_name === 'string' ? m.merchant_name : null,
      sandbox: typeof m.sandbox === 'boolean' ? m.sandbox : null,
      country: typeof m.country === 'string' ? m.country : null,
    }))
    .filter((m) => m.merchant_code)
  if (!parsed.length) return null
  return new SumupMerchantSelectionRequiredError(parsed, err.message)
}

export async function putSumupOrganisationApiKey(
  organisationId: number | string,
  apiKey: string,
  merchantCode?: string | null,
): Promise<SumupOrganisationStatus> {
  const body: { api_key: string; merchant_code?: string } = { api_key: apiKey }
  const code = (merchantCode || '').trim()
  if (code) body.merchant_code = code
  try {
    return await withNotConfigured(() =>
      apiJson<SumupOrganisationStatus>(`/sumup/organisations/${organisationId}/api-key`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    )
  } catch (err: unknown) {
    const selection = parseMerchantSelectionError(err)
    if (selection) throw selection
    throw err
  }
}

/** @deprecated OAuth connect is dormant; UI uses putSumupOrganisationApiKey. */
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

export interface SumupReaderTelemetry {
  id: number
  sumup_reader_id: string
  label: string
  device_identifier: string | null
  device_model: string | null
  telemetry_available: boolean
  online_status: string | null
  battery_level: number | null
  connection_type: string | null
  firmware_version: string | null
  last_activity: string | null
  state: string | null
}

export async function fetchSumupReaderTelemetry(
  organisationId: number | string,
  readerId: number | string,
): Promise<SumupReaderTelemetry> {
  return withNotConfigured(() =>
    apiJson<SumupReaderTelemetry>(
      `/sumup/organisations/${organisationId}/readers/${readerId}/telemetry`,
    ),
  )
}
