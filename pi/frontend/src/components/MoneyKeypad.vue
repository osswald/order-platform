<template>
  <div class="keypad">
    <div class="display">{{ display }}</div>
    <div class="keys">
      <button v-for="d in keys" :key="d" type="button" class="key" @click="press(d)">{{ d }}</button>
    </div>
    <div class="row">
      <button type="button" class="btn" @click="clear">C</button>
      <button type="button" class="btn" @click="back">⌫</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatMoney } from '@/utils/money'

const props = withDefaults(
  defineProps<{
    modelValue?: number
    currency?: string
  }>(),
  { modelValue: 0, currency: 'CHF' },
)

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '00', '0']

const display = computed(() => formatMoney(props.modelValue, props.currency))

function press(d: string) {
  let v = props.modelValue
  if (d === '00') {
    v = Math.min(v * 100, 99999999)
  } else {
    v = Math.min(v * 10 + Number(d), 99999999)
  }
  emit('update:modelValue', v)
}

function clear() {
  emit('update:modelValue', 0)
}

function back() {
  emit('update:modelValue', Math.floor(props.modelValue / 10))
}
</script>

<style scoped>
.keypad {
  margin-top: 0.5rem;
}
.display {
  font-size: 1.5rem;
  font-weight: 700;
  text-align: right;
  padding: 0.5rem 0.75rem;
  background: var(--bg);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  font-variant-numeric: tabular-nums;
}
.keys {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.35rem;
}
.key {
  min-height: 48px;
  font-size: 1.15rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: #334155;
  color: var(--text);
  cursor: pointer;
  touch-action: manipulation;
}
</style>
