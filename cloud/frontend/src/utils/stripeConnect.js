import { apiFetch } from '../api'
import { i18n } from '../i18n'

function t(key) {
  return i18n.global.t(key)
}

async function parseError(res) {
  const text = await res.text()
  try {
    const data = JSON.parse(text)
    return data.detail || data.message || text
  } catch {
    return text || `HTTP ${res.status}`
  }
}

export async function fetchStripeConnectStatus(organisationId) {
  const res = await apiFetch(`/stripe/connect/organisations/${organisationId}/status`)
  if (res.status === 503) {
    return { configured: false, error: t('stripe.notConfigured') }
  }
  if (!res.ok) throw new Error(await parseError(res))
  return { configured: true, ...(await res.json()) }
}

export async function createStripeAccountLink(organisationId) {
  const res = await apiFetch(`/stripe/connect/organisations/${organisationId}/account-link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (res.status === 503) throw new Error(t('stripe.notConfigured'))
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function refreshStripeConnectStatus(organisationId) {
  const res = await apiFetch(`/stripe/connect/organisations/${organisationId}/refresh`, {
    method: 'POST',
  })
  if (res.status === 503) throw new Error(t('stripe.notConfigured'))
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
