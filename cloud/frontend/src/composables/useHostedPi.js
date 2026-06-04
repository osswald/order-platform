import { ref } from 'vue'
import { apiFetch } from '../api'

export function useHostedPi(eventIdRef) {
  const instance = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function load() {
    const eventId = eventIdRef?.value ?? eventIdRef
    if (!eventId) {
      instance.value = null
      return
    }
    loading.value = true
    error.value = ''
    try {
      const response = await apiFetch(`/events/${eventId}/hosted-pi`)
      if (response.status === 404) {
        instance.value = null
        return
      }
      if (!response.ok) {
        throw new Error(await response.text())
      }
      const data = await response.json()
      instance.value = data || null
    } catch (err) {
      error.value = err?.message || 'Cloud-Pi konnte nicht geladen werden.'
      instance.value = null
    } finally {
      loading.value = false
    }
  }

  async function start() {
    const eventId = eventIdRef?.value ?? eventIdRef
    if (!eventId) return null
    loading.value = true
    error.value = ''
    try {
      const response = await apiFetch(`/events/${eventId}/hosted-pi`, { method: 'POST' })
      if (!response.ok) {
        throw new Error(await response.text())
      }
      instance.value = await response.json()
      return instance.value
    } catch (err) {
      error.value = err?.message || 'Cloud-Pi konnte nicht gestartet werden.'
      throw err
    } finally {
      loading.value = false
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
        throw new Error(await response.text())
      }
      instance.value = await response.json()
      return instance.value
    } catch (err) {
      error.value = err?.message || 'Cloud-Pi konnte nicht beendet werden.'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    instance,
    loading,
    error,
    load,
    start,
    stop,
  }
}
