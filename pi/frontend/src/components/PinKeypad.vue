<template>
  <div class="pin-keypad">
    <div class="display" aria-label="Eingegebene Ziffern">
      <span v-for="i in maxLength" :key="i" class="dot" :class="{ filled: i <= value.length }" />
    </div>
    <div class="keys">
      <button v-for="d in digits" :key="d" type="button" class="key" @click="press(d)">{{ d }}</button>
    </div>
    <div class="row actions">
      <button type="button" class="btn" @click="clear">C</button>
      <button type="button" class="btn" @click="backspace">⌫</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  maxLength: { type: Number, default: 6 },
})

const emit = defineEmits(['complete'])

const value = ref('')
const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

function press(d) {
  if (value.value.length >= props.maxLength) return
  value.value += d
}

function clear() {
  value.value = ''
}

function backspace() {
  value.value = value.value.slice(0, -1)
}

watch(value, (v) => {
  if (v.length === props.maxLength) emit('complete', v)
})

defineExpose({ clear })
</script>

<style scoped>
.pin-keypad {
  max-width: 20rem;
  margin: 0 auto;
}
.display {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.25rem;
  margin-bottom: 1rem;
}
.dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: transparent;
}
.dot.filled {
  background: var(--accent);
  border-color: var(--accent);
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
