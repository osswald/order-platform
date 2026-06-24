import { ref } from 'vue'
import { apiFetch } from '../api'
import { i18n } from '../i18n'
import { parseApiErrorDetail } from '../utils/apiError'

function t(key) {
  return i18n.global.t(key)
}

function hostedPiErrorMessage(err, fallback = t('hostedPi.unavailable')) {
  const msg = String(err?.message || '').trim()
  if (
    !msg ||
    msg === 'Failed to fetch' ||
    msg === 'Load failed' ||
    /NetworkError/i.test(msg) ||
    /fetch resource/i.test(msg)
  ) {
    return t('hostedPi.unavailable')
  }
  return msg || fallback
}

export function useHostedPi(eventIdRef) {
  const instance = ref(null)
  const loading = ref(false)
  const starting = ref(false)
  const error = ref('')

  async function load({ silent = false } = {}) {
    const eventId = eventIdRef?.value ?? eventIdRef
    if (!eventId) {
      instance.value = null
      return
    }
    loading.value = true
    if (!silent) {
      error.value = ''
    }
    try {
      const response = await apiFetch(`/events/${eventId}/hosted-pi`)
      if (response.status === 404) {
        instance.value = null
        if (!silent) {
          error.value = ''
        }
        return
      }
      if (!response.ok) {
        const detail = await parseApiErrorDetail(response)
        if (!silent) {
          error.value = detail
          instance.value = null
        }
        return
      }
      const data = await response.json()
      instance.value = data || null
      error.value = ''
    } catch (err) {
      if (!silent) {
        error.value = hostedPiErrorMessage(err, t('hostedPi.loadFailed'))
        instance.value = null
      }
    } finally {
      loading.value = false
    }
  }

  async function start() {
    const eventId = eventIdRef?.value ?? eventIdRef
    if (!eventId) return null
    loading.value = true
    starting.value = true
    error.value = ''
    try {
      const response = await apiFetch(`/events/${eventId}/hosted-pi`, { method: 'POST' })
      if (!response.ok) {
        const detail = await parseApiErrorDetail(response)
        error.value = detail
        throw new Error(detail)
      }
      instance.value = await response.json()
      return instance.value
    } catch (err) {
      if (!error.value) {
        error.value = hostedPiErrorMessage(err, t('hostedPi.startError'))
      }
      throw err
    } finally {
      loading.value = false
      starting.value = false
    }
  }

  async function stop() {
    const eventId = eventIdRef?.value ?? eventIdRef
    if (!eventId) return null
    loading.value = true
    error.value = ''
    try {
      const response = await apiFetch(`/events/${eventId}/hosted-pi`, { method: 'DELETE' })
      if (!response.ok) {
        const detail = await parseApiErrorDetail(response)
        error.value = detail
        throw new Error(detail)
      }
      instance.value = await response.json()
      return instance.value
    } catch (err) {
      if (!error.value) {
        error.value = hostedPiErrorMessage(err, t('hostedPi.stopFailed'))
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    instance,
    loading,
    starting,
    error,
    load,
    start,
    stop,
  }
}
