<template>
  <div
    ref="el"
    class="sheet-scroll"
    :class="{ 'sheet-scroll--above': hasAbove, 'sheet-scroll--below': hasBelow }"
    @scroll="update"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    active?: boolean
  }>(),
  { active: true },
)

const el = ref<HTMLElement | null>(null)
const hasAbove = ref(false)
const hasBelow = ref(false)

function update() {
  const node = el.value
  if (!node) {
    hasAbove.value = false
    hasBelow.value = false
    return
  }
  const { scrollTop, clientHeight, scrollHeight } = node
  hasAbove.value = scrollTop > 0
  hasBelow.value = scrollTop + clientHeight < scrollHeight - 1
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  resizeObserver = new ResizeObserver(() => update())
  if (el.value) resizeObserver.observe(el.value)
  update()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

watch(
  () => props.active,
  async (isActive) => {
    if (isActive) {
      await nextTick()
      update()
    }
  },
)
</script>
