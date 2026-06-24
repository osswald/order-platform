import { ref } from 'vue'
import { apiJson } from '../api'
import { i18n } from '../i18n'

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
      const data = await apiJson(`/events/${eventId}/hosted-pi`)
      instance.value = data || null
      error.value = ''
    } catch (err) {
      if (err?.status === 404) {
        instance.value = null
        if (!silent) {
          error.value = ''
        }
        return
      }
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
      instance.value = await apiJson(`/events/${eventId}/hosted-pi`, { method: 'POST' })
      return instance.value
    } catch (err) {
      error.value = hostedPiErrorMessage(err, t('hostedPi.startError'))
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
      instance.value = await apiJson(`/events/${eventId}/hosted-pi`, { method: 'DELETE' })
      return instance.value
    } catch (err) {
      error.value = hostedPiErrorMessage(err, t('hostedPi.stopFailed'))
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
