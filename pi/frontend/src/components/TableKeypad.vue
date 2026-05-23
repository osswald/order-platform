<template>
  <div class="table-keypad">
    <p class="muted">{{ hint }}</p>
    <div class="display">{{ displayValue || '—' }}</div>
    <div class="keys">
      <button v-for="d in digits" :key="d" type="button" class="key" @click="press(d)">{{ d }}</button>
    </div>
    <div class="row actions">
      <button type="button" class="btn" @click="clear">C</button>
      <button type="button" class="btn" @click="backspace">⌫</button>
      <button type="button" class="btn primary" :disabled="!canOk" @click="ok">OK</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  hint: { type: String, default: 'Tischnummer (1–99999)' },
  maxLength: { type: Number, default: 5 },
})

const emit = defineEmits(['submit'])

const value = ref('')
const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

const displayValue = computed(() => value.value)
const canOk = computed(() => {
  const n = parseInt(value.value, 10)
  return n >= 1 && n <= 99999
})

function press(d) {
  if (value.value.length >= props.maxLength) return
  if (value.value === '0') value.value = d
  else value.value += d
}

function clear() {
  value.value = ''
}

function backspace() {
  value.value = value.value.slice(0, -1)
}

function ok() {
  const n = parseInt(value.value, 10)
  if (n >= 1 && n <= 99999) emit('submit', n)
}
</script>

<style scoped>
.table-keypad {
  max-width: 20rem;
  margin: 0 auto;
}
.display {
  font-size: 2rem;
  font-weight: 700;
  text-align: center;
  padding: 1rem;
  background: var(--card);
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  font-variant-numeric: tabular-nums;
}
.keys {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}
.key {
  min-height: 52px;
  font-size: 1.25rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  touch-action: manipulation;
}
.actions {
  margin-top: 1rem;
  justify-content: stretch;
}
.actions .btn {
  flex: 1;
}
</style>
