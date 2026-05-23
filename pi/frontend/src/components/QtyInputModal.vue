<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="$emit('close')" />
    <div v-if="open" class="modal" role="dialog" aria-modal="true">
      <h3>Menge</h3>
      <p class="muted">{{ name }}</p>
      <div class="qty-display">{{ value }}</div>
      <div class="keys">
        <button v-for="d in digits" :key="d" type="button" class="key" @click="press(d)">{{ d }}</button>
      </div>
      <div class="row actions">
        <button type="button" class="btn" @click="clear">C</button>
        <button type="button" class="btn" @click="$emit('close')">Abbrechen</button>
        <button type="button" class="btn primary" @click="confirm">OK</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  name: { type: String, default: '' },
  max: { type: Number, default: 99 },
  modelValue: { type: Number, default: 0 },
})

const emit = defineEmits(['close', 'confirm'])

const value = ref('0')
const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

watch(
  () => props.open,
  (o) => {
    if (o) value.value = String(props.modelValue ?? 0)
  },
)

function press(d) {
  const next = value.value === '0' ? d : value.value + d
  const n = parseInt(next, 10)
  if (n <= props.max) value.value = String(n)
}

function clear() {
  value.value = '0'
}

function confirm() {
  emit('confirm', Math.min(props.max, Math.max(0, parseInt(value.value, 10) || 0)))
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 200;
}
.modal {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 201;
  background: var(--card);
  border-radius: 0.75rem;
  padding: 1rem;
  width: min(20rem, 92vw);
}
.qty-display {
  font-size: 2rem;
  font-weight: 700;
  text-align: center;
  margin: 0.75rem 0;
}
.keys {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.35rem;
}
.key {
  min-height: 48px;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 1.15rem;
}
.actions {
  margin-top: 0.75rem;
  gap: 0.35rem;
}
.actions .btn {
  flex: 1;
}
</style>
