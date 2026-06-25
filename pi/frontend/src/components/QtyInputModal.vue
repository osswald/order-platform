<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="qty-modal-overlay"
      role="presentation"
      @click.self="$emit('close')"
    >
      <div class="qty-modal" role="dialog" aria-modal="true" @click.stop>
        <h3>Menge</h3>
        <p class="muted">{{ name }}</p>
        <p v-if="maxHint" class="max-hint muted">{{ maxHint }}</p>
        <div class="qty-display" aria-live="polite">{{ value }}</div>
        <div class="keys">
          <button
            v-for="d in digitKeys"
            :key="d"
            type="button"
            class="key"
            @click="press(d)"
          >
            {{ d }}
          </button>
        </div>
        <div class="row actions">
          <button type="button" class="btn key-action" @click="clear">C</button>
          <button type="button" class="btn key-action" @click="backspace" aria-label="Löschen">
            ⌫
          </button>
          <button type="button" class="btn primary key-action" @click="confirm">OK</button>
        </div>
        <button type="button" class="btn cancel-btn" @click="$emit('close')">Abbrechen</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    name?: string
    max?: number
    modelValue?: number
  }>(),
  { open: false, name: '', max: 99, modelValue: 0 },
)

const emit = defineEmits<{
  close: []
  confirm: [qty: number]
}>()

const value = ref('0')
const digitKeys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

const maxHint = computed(() => (props.max < 999 ? `max. ${props.max}` : ''))

watch(
  () => props.open,
  (o) => {
    if (o) value.value = String(Math.max(0, Math.min(props.max, props.modelValue ?? 0)))
  },
)

function press(d: string) {
  const next = value.value === '0' ? d : `${value.value}${d}`
  const n = parseInt(next, 10)
  if (Number.isNaN(n) || n > props.max) return
  value.value = String(n)
}

function backspace() {
  if (value.value.length <= 1) {
    value.value = '0'
    return
  }
  const next = value.value.slice(0, -1)
  value.value = next === '' ? '0' : next
}

function clear() {
  value.value = '0'
}

function confirm() {
  const n = parseInt(value.value, 10) || 0
  emit('confirm', Math.min(props.max, Math.max(0, n)))
}
</script>

<style scoped>
.qty-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 220;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: calc(0.75rem + var(--safe-top)) 0.75rem calc(0.75rem + var(--safe-bottom));
  background: rgba(0, 0, 0, 0.5);
  touch-action: manipulation;
}

.qty-modal {
  width: min(20rem, 100%);
  background: var(--card);
  border-radius: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--border);
  /* Flex centering on overlay — avoid transform (breaks touches in Android WebView). */
}

.qty-display {
  font-size: 2rem;
  font-weight: 700;
  text-align: center;
  margin: 0.75rem 0;
  font-variant-numeric: tabular-nums;
}

.max-hint {
  margin: -0.35rem 0 0.5rem;
  font-size: 0.85rem;
  text-align: center;
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
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.actions {
  margin-top: 0.75rem;
  gap: 0.35rem;
}

.key-action {
  flex: 1;
  min-height: 48px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.cancel-btn {
  width: 100%;
  margin-top: 0.5rem;
  min-height: 44px;
  touch-action: manipulation;
}
</style>
