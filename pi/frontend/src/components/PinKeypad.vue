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

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    maxLength?: number
    /** When provided (including via v-model), parent owns the value; local state stays in sync. */
    modelValue?: string
    /** When true (default), emit `complete` once length reaches maxLength. */
    autoComplete?: boolean
  }>(),
  { maxLength: 6, autoComplete: true },
)

const emit = defineEmits<{
  complete: [pin: string]
  'update:modelValue': [value: string]
}>()

const value = ref(props.modelValue ?? '')
const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

watch(
  () => props.modelValue,
  (v) => {
    if (v !== undefined && v !== value.value) {
      value.value = v
    }
  },
)

function setValue(next: string) {
  value.value = next
  emit('update:modelValue', next)
  if (props.autoComplete && next.length === props.maxLength) {
    emit('complete', next)
  }
}

function press(d: string) {
  if (value.value.length >= props.maxLength) return
  setValue(value.value + d)
}

function clear() {
  setValue('')
}

function backspace() {
  setValue(value.value.slice(0, -1))
}

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
