import { computed } from 'vue'

const version = import.meta.env.VITE_APP_VERSION || 'dev'
const buildTime = import.meta.env.VITE_BUILD_TIME || ''

export function useAppVersion() {
  const label = computed(() => {
    const base = `v${version}`
    return buildTime && buildTime !== 'dev' ? `${base} (${buildTime})` : base
  })

  return { version, buildTime, label }
}
