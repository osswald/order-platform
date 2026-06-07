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

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  maxHeight: { type: String, default: '' },
})

defineEmits(['pick'])

const listStyle = computed(() => {
  if (!props.maxHeight) return undefined
  return { maxHeight: props.maxHeight, overflowY: 'auto' }
})

function metaFor(item) {
  return item.meta ?? item.priceLabel ?? ''
}
</script>
