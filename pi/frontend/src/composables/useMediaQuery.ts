import { onMounted, onUnmounted, ref } from 'vue'

export function useMediaQuery(query: string) {
  const matches = ref(false)
  let mql: MediaQueryList | null = null
  let update: (() => void) | null = null

  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    mql = window.matchMedia(query)
    update = () => {
      matches.value = mql!.matches
    }
    update()
    mql.addEventListener('change', update)
  })

  onUnmounted(() => {
    if (mql && update) {
      mql.removeEventListener('change', update)
    }
  })

  return matches
}
