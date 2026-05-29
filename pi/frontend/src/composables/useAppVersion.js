import { computed } from 'vue'

const version = import.meta.env.VITE_APP_VERSION || 'dev'
const buildSha = import.meta.env.VITE_BUILD_SHA || ''

export function useAppVersion() {
  const label = computed(() => {
    const base = `v${version}`
    return buildSha && buildSha !== 'dev' ? `${base} (${buildSha})` : base
  })

  return { version, buildSha, label }
}
