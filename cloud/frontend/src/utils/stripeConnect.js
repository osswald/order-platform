import { apiJson } from '../api'
import { i18n } from '../i18n'

function t(key) {
  return i18n.global.t(key)
}

export async function fetchStripeConnectStatus(organisationId) {
  try {
    const data = await apiJson(`/stripe/connect/organisations/${organisationId}/status`)
    return { configured: true, ...data }
  } catch (err) {
    if (err.status === 503) {
      return { configured: false, error: t('stripe.notConfigured') }
    }
    throw err
  }
}

export async function createStripeAccountLink(organisationId) {
  try {
    return await apiJson(`/stripe/connect/organisations/${organisationId}/account-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
  } catch (err) {
    if (err.status === 503) throw new Error(t('stripe.notConfigured'))
    throw err
  }
}

export async function refreshStripeConnectStatus(organisationId) {
  try {
    return await apiJson(`/stripe/connect/organisations/${organisationId}/refresh`, {
      method: 'POST',
    })
  } catch (err) {
    if (err.status === 503) throw new Error(t('stripe.notConfigured'))
    throw err
  }
}
