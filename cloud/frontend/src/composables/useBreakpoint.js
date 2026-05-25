import { onMounted, onUnmounted, ref } from 'vue'

export function useBreakpoint(maxWidthPx) {
  const matches = ref(false)
  let mediaQuery = null

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
