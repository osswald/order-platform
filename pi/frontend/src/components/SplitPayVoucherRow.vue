<template>
  <li class="split-line top voucher-line">
    <span class="cell qty" aria-hidden="true">·</span>
    <span class="cell name">
      <span class="name-text">{{ label }}</span>
    </span>
    <button type="button" class="cell price" :aria-label="`${label} entfernen`" @click="$emit('remove')">
      {{ amountLabel }}
    </button>
  </li>
</template>

<script setup>
import { computed } from 'vue'
import { formatAmount } from '../utils/money'

const props = defineProps({
  label: { type: String, required: true },
  amountCents: { type: Number, required: true },
})

defineEmits(['remove'])

const amountLabel = computed(() => {
  const c = Math.max(0, Number(props.amountCents) || 0)
  return `−${formatAmount(c)}`
})
</script>
