import { computed, ref } from 'vue'
import { api } from '../api'

const status = ref(null)
const loaded = ref(false)
let loadPromise = null

export async function fetchSetupStatus() {
  if (loadPromise) return loadPromise
  loadPromise = api('/v1/setup/status')
    .then((body) => {
      status.value = body
      loaded.value = true
      return body
    })
    .catch(() => {
      status.value = null
      loaded.value = true
      return null
    })
  return loadPromise
}

export function useSetupStatus() {
  const configured = computed(() => Boolean(status.value?.configured))
  const emulatedPrinter = computed(() => Boolean(status.value?.emulated_printer))

  return {
    status,
    loaded,
    configured,
    emulatedPrinter,
    fetchSetupStatus,
  }
}
