import { ref, unref, type Ref } from 'vue'
import { apiJson } from '../api'
import { i18n } from '../i18n'
import type { HostedPiRead } from '@/types/api'
import { isApiError } from '@/types/api'

function t(key: string) {
  return i18n.global.t(key)
}

function hostedPiErrorMessage(err: unknown, fallback = t('hostedPi.unavailable')) {
  const msg = isApiError(err) ? String(err.message || '').trim() : ''
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

export function useHostedPi(eventIdRef: Ref<number | undefined> | number | undefined) {
  const instance = ref<HostedPiRead | null>(null)
  const loading = ref(false)
  const starting = ref(false)
  const error = ref('')

  function resolveEventId() {
    return unref(eventIdRef)
  }

  async function load({ silent = false } = {}) {
    const eventId = resolveEventId()
    if (!eventId) {
      instance.value = null
      return
    }
    loading.value = true
    if (!silent) {
      error.value = ''
    }
    try {
      const data = await apiJson<HostedPiRead | null>(`/events/${eventId}/hosted-pi`)
      instance.value = data || null
      error.value = ''
    } catch (err: unknown) {
      if (isApiError(err) && err.status === 404) {
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
    const eventId = resolveEventId()
    if (!eventId) return null
    loading.value = true
    starting.value = true
    error.value = ''
    try {
      instance.value = await apiJson<HostedPiRead>(`/events/${eventId}/hosted-pi`, { method: 'POST' })
      return instance.value
    } catch (err: unknown) {
      error.value = hostedPiErrorMessage(err, t('hostedPi.startError'))
      throw err
    } finally {
      loading.value = false
      starting.value = false
    }
  }

  async function stop() {
    const eventId = resolveEventId()
    if (!eventId) return null
    loading.value = true
    error.value = ''
    try {
      instance.value = await apiJson<HostedPiRead>(`/events/${eventId}/hosted-pi`, { method: 'DELETE' })
      return instance.value
    } catch (err: unknown) {
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
