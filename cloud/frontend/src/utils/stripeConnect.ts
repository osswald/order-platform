import { apiJson } from '../api'
import { i18n } from '../i18n'
import type { StripeAccountLinkResponse, StripeConnectStatus } from '@/types/api'
import { isApiError } from '@/types/api'

function t(key: string): string {
  return i18n.global.t(key)
}

export type StripeConnectStatusView =
  | ({ configured: true } & StripeConnectStatus)
  | { configured: false; error: string }

export async function fetchStripeConnectStatus(
  organisationId: number | string,
): Promise<StripeConnectStatusView> {
  try {
    const data = await apiJson<StripeConnectStatus>(
      `/stripe/connect/organisations/${organisationId}/status`,
    )
    return { configured: true, ...data }
  } catch (err: unknown) {
    if (isApiError(err) && err.status === 503) {
      return { configured: false, error: t('stripe.notConfigured') }
    }
    throw err
  }
}

export async function createStripeAccountLink(
  organisationId: number | string,
): Promise<StripeAccountLinkResponse> {
  try {
    return await apiJson<StripeAccountLinkResponse>(
      `/stripe/connect/organisations/${organisationId}/account-link`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      },
    )
  } catch (err: unknown) {
    if (isApiError(err) && err.status === 503) throw new Error(t('stripe.notConfigured'))
    throw err
  }
}

export async function refreshStripeConnectStatus(
  organisationId: number | string,
): Promise<StripeConnectStatus> {
  try {
    return await apiJson<StripeConnectStatus>(
      `/stripe/connect/organisations/${organisationId}/refresh`,
      {
        method: 'POST',
      },
    )
  } catch (err: unknown) {
    if (isApiError(err) && err.status === 503) throw new Error(t('stripe.notConfigured'))
    throw err
  }
}
