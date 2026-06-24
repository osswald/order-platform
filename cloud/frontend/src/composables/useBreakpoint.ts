import { onMounted, onUnmounted, ref } from 'vue'

export function useBreakpoint(maxWidthPx: number) {
  const matches = ref(false)
  let mediaQuery: MediaQueryList | null = null

  function update() {
    matches.value = mediaQuery?.matches ?? false
  }

  onMounted(() => {
    mediaQuery = window.matchMedia(`(max-width: ${maxWidthPx}px)`)
    update()
    mediaQuery.addEventListener('change', update)
  })

  onUnmounted(() => {
    mediaQuery?.removeEventListener('change', update)
  })

  return { matches }
}
