import { computed, ref } from 'vue'
import { api } from '@/api'
import type { SetupStatusResponse } from '@/types/api'

const status = ref<SetupStatusResponse | null>(null)
const loaded = ref(false)
let loadPromise: Promise<SetupStatusResponse | null> | null = null

export async function fetchSetupStatus(): Promise<SetupStatusResponse | null> {
  if (loadPromise) return loadPromise
  loadPromise = api<SetupStatusResponse>('/v1/setup/status')
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
