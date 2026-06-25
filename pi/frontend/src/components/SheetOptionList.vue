<template>
  <ul class="sheet-option-list" :style="listStyle">
    <li v-for="(item, idx) in items" :key="item.key ?? idx" class="sheet-option-row">
      <button
        type="button"
        class="sheet-option-row__control sheet-option-row__control--btn"
        @click="$emit('pick', item)"
      >
        <span class="sheet-option-row__name">{{ item.label }}</span>
        <span v-if="metaFor(item)" class="sheet-option-row__meta">{{ metaFor(item) }}</span>
      </button>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'

export interface SheetOptionItem {
  key?: string | number
  label?: string
  meta?: string
  priceLabel?: string
  [key: string]: unknown
}

const props = withDefaults(
  defineProps<{
    items?: SheetOptionItem[]
    maxHeight?: string
  }>(),
  { items: () => [], maxHeight: '' },
)

defineEmits<{
  pick: [item: SheetOptionItem]
}>()

const listStyle = computed((): CSSProperties | undefined => {
  if (!props.maxHeight) return undefined
  return { maxHeight: props.maxHeight, overflowY: 'auto' }
})

function metaFor(item: SheetOptionItem): string {
  return item.meta ?? item.priceLabel ?? ''
}
</script>
