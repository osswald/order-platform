import { computed, type ComputedRef } from 'vue'

const version = import.meta.env.VITE_APP_VERSION || 'dev'
const buildTime = import.meta.env.VITE_BUILD_TIME || ''

export function useAppVersion(): {
  version: string
  buildTime: string
  label: ComputedRef<string>
} {
  const label = computed(() => {
    const base = `v${version}`
    return buildTime && buildTime !== 'dev' ? `${base} (${buildTime})` : base
  })

  return { version, buildTime, label }
}
